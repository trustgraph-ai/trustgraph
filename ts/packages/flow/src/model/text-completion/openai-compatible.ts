/**
 * OpenAI-compatible text completion service (generic local server).
 *
 * Works with LM Studio, llama.cpp, vLLM, Ollama OpenAI-compat endpoint, etc.
 *
 * Env:
 *   OPENAI_COMPAT_URL   (required – e.g. http://localhost:1234/v1)
 *   OPENAI_COMPAT_KEY   (default: sk-no-key-required)
 *   OPENAI_COMPAT_MODEL (default: default)
 */

import OpenAI from "openai";
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
  providerStatusError,
  requiredString,
  toAsyncGenerator,
  type TextCompletionRuntimeError,
} from "./common.ts";

export type OpenAICompatibleProcessorConfig = ProcessorConfig & {
  model?: string;
  apiKey?: string;
  baseUrl?: string;
  temperature?: number;
  maxOutput?: number;
};

type ResolvedOpenAICompatibleConfig = {
  readonly defaultModel: string;
  readonly defaultTemperature: number;
  readonly maxOutput: number;
  readonly apiKey: string;
  readonly baseURL: string;
};

const loadOpenAICompatibleConfig = Effect.fn("loadOpenAICompatibleConfig")(function*(
  config: OpenAICompatibleProcessorConfig,
) {
    const defaultModel =
      config.model ?? (yield* optionalStringConfig("OpenAI-Compatible", "OPENAI_COMPAT_MODEL")) ?? "default";
    const baseURL = yield* requiredString(
      config.baseUrl ?? (yield* optionalStringConfig("OpenAI-Compatible", "OPENAI_COMPAT_URL")),
      "OpenAI-Compatible",
      "OPENAI_COMPAT_URL",
      "OpenAI-compatible server URL not specified (set OPENAI_COMPAT_URL)",
    );
    const apiKey =
      config.apiKey ?? (yield* optionalStringConfig("OpenAI-Compatible", "OPENAI_COMPAT_KEY")) ?? "sk-no-key-required";

    return {
      defaultModel,
      defaultTemperature: config.temperature ?? 0.0,
      maxOutput: config.maxOutput ?? 4096,
      apiKey,
      baseURL,
    } satisfies ResolvedOpenAICompatibleConfig;
});

const mapOpenAICompatibleError = (error: unknown): TextCompletionRuntimeError =>
  providerStatusError("OpenAI-Compatible", error);

export function makeOpenAICompatibleProvider(
  config: OpenAICompatibleProcessorConfig,
): LlmProvider {
  const {
    defaultModel,
    defaultTemperature,
    maxOutput,
    apiKey,
    baseURL,
  } = Effect.runSync(loadOpenAICompatibleConfig(config)) satisfies ResolvedOpenAICompatibleConfig;

  const client = new OpenAI({ baseURL, apiKey });

  Effect.runSync(Effect.log("[OpenAI-Compatible] LLM service initialized"));

  return {
    generateContent: (
      system: string,
      prompt: string,
      model?: string,
      temperature?: number,
    ): Promise<LlmResult> => {
      const modelName = model ?? defaultModel;
      const temp = temperature ?? defaultTemperature;

      return Effect.runPromise(
        Effect.tryPromise({
          try: () =>
            client.chat.completions.create({
              model: modelName,
              messages: [
                { role: "system", content: system },
                { role: "user", content: prompt },
              ],
              temperature: temp,
              max_tokens: maxOutput,
            }),
          catch: mapOpenAICompatibleError,
        }).pipe(
          Effect.map((resp): LlmResult => ({
            text: resp.choices[0].message.content ?? "",
            inToken: resp.usage?.prompt_tokens ?? 0,
            outToken: resp.usage?.completion_tokens ?? 0,
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
      temperature?: number,
    ): AsyncGenerator<LlmChunk> => {
      const modelName = model ?? defaultModel;
      const temp = temperature ?? defaultTemperature;

      const stream = Stream.fromEffect(
        Effect.tryPromise({
          try: () =>
            client.chat.completions.create({
              model: modelName,
              messages: [
                { role: "system", content: system },
                { role: "user", content: prompt },
              ],
              temperature: temp,
              max_tokens: maxOutput,
              stream: true,
            }),
          catch: mapOpenAICompatibleError,
        }),
      ).pipe(
        Stream.flatMap((openAIStream) => {
          const iterator = openAIStream[Symbol.asyncIterator]();
      let totalInputTokens = 0;
      let totalOutputTokens = 0;

          return Stream.unfold<"pulling" | "done", LlmChunk, TextCompletionRuntimeError, never>(
            "pulling",
            (state) => {
              if (state === "done") return Effect.void as Effect.Effect<undefined>;

              return Effect.gen(function* () {
                while (true) {
                  const next = yield* Effect.tryPromise({
                    try: () => iterator.next(),
                    catch: mapOpenAICompatibleError,
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
                  const content = chunk.choices[0]?.delta?.content;
                  if (chunk.usage !== null && chunk.usage !== undefined) {
                    totalInputTokens = chunk.usage.prompt_tokens;
                    totalOutputTokens = chunk.usage.completion_tokens;
                  }
                  if (content !== null && content !== undefined && content.length > 0) {
                    return [{
                      text: content,
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

      return toAsyncGenerator(Stream.toAsyncIterable(stream), mapOpenAICompatibleError);
    },
  };
}

export type OpenAICompatibleProcessor = ReturnType<typeof makeOpenAICompatibleProcessor>;

export function makeOpenAICompatibleProcessor(
  config: OpenAICompatibleProcessorConfig,
): ReturnType<typeof makeLlmService> {
  return makeLlmService(config, makeOpenAICompatibleProvider(config));
}

export const OpenAICompatibleProcessor = makeOpenAICompatibleProcessor;

export const program = makeFlowProcessorProgram<ProcessorConfig, never, Llm>({
  id: "text-completion",
  specs: () => makeLlmSpecs(),
  layer: (config) =>
    Layer.succeed(
      Llm,
      Llm.of(makeLlmServiceShape(makeOpenAICompatibleProvider(config))),
    ),
});

const openAICompatibleTextCompletionRuntime = ManagedRuntime.make(Layer.empty);

export function run(): Promise<void> {
  return openAICompatibleTextCompletionRuntime.runPromise(program);
}

export function runMain(): void {
  NodeRuntime.runMain(program);
}
