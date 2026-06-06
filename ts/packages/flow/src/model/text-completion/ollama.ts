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
  makeLlmService,
  makeFlowProcessorProgram,
  makeLlmSpecs,
  type Llm,
  type LlmProvider,
  type ProcessorConfig,
  type LlmResult,
} from "@trustgraph/base";
import { Effect, Stream } from "effect";
import {
  llmStreamPart,
  makeTextCompletionLayer,
  optionalStringConfig,
  providerRuntimeError,
  streamTextCompletionChunks,
  type TextCompletionConfigError,
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

const makeOllamaProviderFromClient = (
  resolved: ResolvedOllamaConfig,
  client: Ollama,
): LlmProvider<TextCompletionRuntimeError> => {
  const { defaultModel } = resolved;

  return {
    generateContent: (
      system: string,
      prompt: string,
      model?: string,
      _temperature?: number,
    ) => {
      const modelName = model ?? defaultModel;
      const fullPrompt = system + "\n\n" + prompt;

      return Effect.tryPromise({
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
      );
    },
    supportsStreaming: () => true,
    generateContentStream: (
      system: string,
      prompt: string,
      model?: string,
      _temperature?: number,
    ) => {
      const modelName = model ?? defaultModel;
      const fullPrompt = system + "\n\n" + prompt;

      return Stream.fromEffect(
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
        Stream.flatMap((ollamaStream) =>
          streamTextCompletionChunks(ollamaStream, {
            model: modelName,
            mapError: mapOllamaError,
            extract: (chunk) =>
              llmStreamPart({
                text: chunk.response,
                inToken: chunk.prompt_eval_count,
                outToken: chunk.eval_count,
              }),
          })
        ),
      );
    },
  } satisfies LlmProvider<TextCompletionRuntimeError>;
};

export function makeOllamaProvider(
  config: OllamaProcessorConfig,
): LlmProvider<TextCompletionRuntimeError> {
  return Effect.runSync(makeOllamaProviderEffect(config));
}

export const makeOllamaProviderEffect = Effect.fn("makeOllamaProvider")(function*(
  config: OllamaProcessorConfig,
) {
  const resolved = yield* loadOllamaConfig(config);
  const client = yield* Effect.try({
    try: () => new Ollama({ host: resolved.host }),
    catch: mapOllamaError,
  });

  yield* Effect.log(
    `[Ollama] LLM service initialized (host=${resolved.host}, model=${resolved.defaultModel})`,
  );
  return makeOllamaProviderFromClient(resolved, client);
});

export type OllamaProcessor = ReturnType<typeof makeOllamaProcessor>;

export function makeOllamaProcessor(
  config: OllamaProcessorConfig,
): ReturnType<typeof makeLlmService> {
  return makeLlmService(config, makeOllamaProvider(config));
}

export const OllamaProcessor = makeOllamaProcessor;

export const program = makeFlowProcessorProgram<
  OllamaProcessorConfig,
  TextCompletionConfigError | TextCompletionRuntimeError,
  Llm
>({
  id: "text-completion",
  specs: () => makeLlmSpecs(),
  layer: (config) => makeTextCompletionLayer(makeOllamaProviderEffect(config)),
});

export function runMain(): void {
  NodeRuntime.runMain(program);
}
