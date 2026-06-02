/**
 * Ollama text completion service.
 *
 * Connects to a local Ollama instance for text generation.
 *
 * Python reference: trustgraph-flow/trustgraph/model/text_completion/ollama/llm.py
 */

import { Ollama } from "ollama";
import { NodeRuntime } from "@effect/platform-node";
import {
  Llm,
  makeLlmService,
  makeFlowProcessorProgram,
  makeLlmServiceShape,
  makeLlmSpecs,
  type LlmProvider,
  type ProcessorConfig,
  type LlmResult,
  type LlmChunk,
} from "@trustgraph/base";
import { Effect, Layer, ManagedRuntime, Stream } from "effect";
import {
  optionalStringConfig,
  providerRuntimeError,
  toAsyncGenerator,
  type TextCompletionRuntimeError,
} from "./common.ts";

export type OllamaProcessorConfig = ProcessorConfig & {
  model?: string;
  ollamaUrl?: string;
};

type ResolvedOllamaConfig = {
  readonly defaultModel: string;
  readonly host: string;
};

const loadOllamaConfig = Effect.fn("loadOllamaConfig")(function*(config: OllamaProcessorConfig) {
    return {
      defaultModel:
        config.model ??
        (yield* optionalStringConfig("Ollama", "OLLAMA_MODEL")) ??
        "qwen2.5:0.5b",
      host:
        config.ollamaUrl ??
        (yield* optionalStringConfig("Ollama", "OLLAMA_URL")) ??
        "http://localhost:11434",
    } satisfies ResolvedOllamaConfig;
});

const mapOllamaError = (error: unknown): TextCompletionRuntimeError =>
  providerRuntimeError("Ollama", error);

export function makeOllamaProvider(config: OllamaProcessorConfig): LlmProvider {
  const { defaultModel, host } = Effect.runSync(loadOllamaConfig(config)) satisfies ResolvedOllamaConfig;

  const client = new Ollama({ host });

  Effect.runSync(Effect.log(
    `[Ollama] LLM service initialized (host=${host}, model=${defaultModel})`,
  ));

  return {
    generateContent: (
      system: string,
      prompt: string,
      model?: string,
      _temperature?: number,
    ): Promise<LlmResult> => {
      const modelName = model ?? defaultModel;
      const fullPrompt = system + "\n\n" + prompt;

      return Effect.runPromise(
        Effect.tryPromise({
          try: () =>
            client.generate({
              model: modelName,
              prompt: fullPrompt,
              stream: false,
            }),
          catch: mapOllamaError,
        }).pipe(
          Effect.map((resp): LlmResult => ({
            text: resp.response,
            inToken: resp.prompt_eval_count ?? 0,
            outToken: resp.eval_count ?? 0,
            model: modelName,
          })),
        ),
      );
    },
    supportsStreaming: () => true,
    generateContentStream: (
      system: string,
      prompt: string,
      model?: string,
      _temperature?: number,
    ): AsyncGenerator<LlmChunk> => {
      const modelName = model ?? defaultModel;
      const fullPrompt = system + "\n\n" + prompt;

      const stream = Stream.fromEffect(
        Effect.tryPromise({
          try: () =>
            client.generate({
              model: modelName,
              prompt: fullPrompt,
              stream: true,
            }),
          catch: mapOllamaError,
        }),
      ).pipe(
        Stream.flatMap((ollamaStream) => {
          const iterator = ollamaStream[Symbol.asyncIterator]();
      let totalInputTokens = 0;
      let totalOutputTokens = 0;

          return Stream.unfold<"pulling" | "done", LlmChunk, TextCompletionRuntimeError, never>(
            "pulling",
            (state) => {
              if (state === "done") return Effect.as(Effect.void, undefined);

              return Effect.gen(function* () {
                while (true) {
                  const next = yield* Effect.tryPromise({
                    try: () => iterator.next(),
                    catch: mapOllamaError,
                  });

                  if (next.done === true) {
                    return [{
                      text: "",
                      inToken: totalInputTokens,
                      outToken: totalOutputTokens,
                      model: modelName,
                      isFinal: true,
                    }, "done"] as const;
                  }

                  const chunk = next.value;
                  if (chunk.prompt_eval_count !== undefined) {
                    totalInputTokens = chunk.prompt_eval_count;
                  }
                  if (chunk.eval_count !== undefined) {
                    totalOutputTokens = chunk.eval_count;
                  }

                  if (chunk.response.length > 0) {
                    return [{
                      text: chunk.response,
                      inToken: null,
                      outToken: null,
                      model: modelName,
                      isFinal: false,
                    }, "pulling"] as const;
                  }
                }
              });
            },
          );
        }),
      );

      return toAsyncGenerator(Stream.toAsyncIterable(stream), mapOllamaError);
    },
  };
}

export type OllamaProcessor = ReturnType<typeof makeOllamaProcessor>;

export function makeOllamaProcessor(
  config: OllamaProcessorConfig,
): ReturnType<typeof makeLlmService> {
  return makeLlmService(config, makeOllamaProvider(config));
}

export const OllamaProcessor = makeOllamaProcessor;

export const program = makeFlowProcessorProgram<ProcessorConfig, never, Llm>({
  id: "text-completion",
  specs: () => makeLlmSpecs(),
  layer: (config) =>
    Layer.succeed(
      Llm,
      Llm.of(makeLlmServiceShape(makeOllamaProvider(config))),
    ),
});

const ollamaTextCompletionRuntime = ManagedRuntime.make(Layer.empty);

export function run(): Promise<void> {
  return ollamaTextCompletionRuntime.runPromise(program);
}

export function runMain(): void {
  NodeRuntime.runMain(program);
}
