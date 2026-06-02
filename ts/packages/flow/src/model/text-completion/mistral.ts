/**
 * Mistral text completion service.
 *
 * Env:
 *   MISTRAL_TOKEN (required – Mistral API key)
 *   MISTRAL_MODEL (default: ministral-8b-latest)
 */

import { Mistral } from "@mistralai/mistralai";
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

export type MistralProcessorConfig = ProcessorConfig & {
  model?: string;
  apiKey?: string;
  temperature?: number;
  maxOutput?: number;
};

type ResolvedMistralConfig = {
  readonly defaultModel: string;
  readonly defaultTemperature: number;
  readonly maxOutput: number;
  readonly apiKey: string;
};

const loadMistralConfig = Effect.fn("loadMistralConfig")(function*(config: MistralProcessorConfig) {
    const apiKey = yield* requiredString(
      config.apiKey ?? (yield* optionalStringConfig("Mistral", "MISTRAL_TOKEN")),
      "Mistral",
      "MISTRAL_TOKEN",
      "Mistral API key not specified",
    );

    return {
      defaultModel:
        config.model ??
        (yield* optionalStringConfig("Mistral", "MISTRAL_MODEL")) ??
        "ministral-8b-latest",
      defaultTemperature: config.temperature ?? 0.0,
      maxOutput: config.maxOutput ?? 4096,
      apiKey,
    } satisfies ResolvedMistralConfig;
});

const mapMistralError = (error: unknown): TextCompletionRuntimeError =>
  providerStatusError("Mistral", error);

export function makeMistralProvider(config: MistralProcessorConfig): LlmProvider {
  const {
    defaultModel,
    defaultTemperature,
    maxOutput,
    apiKey,
  } = Effect.runSync(loadMistralConfig(config)) satisfies ResolvedMistralConfig;

  const client = new Mistral({ apiKey });

  Effect.runSync(Effect.log("[Mistral] LLM service initialized"));

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
            client.chat.complete({
              model: modelName,
              messages: [
                { role: "system", content: system },
                { role: "user", content: prompt },
              ],
              temperature: temp,
              maxTokens: maxOutput,
            }),
          catch: mapMistralError,
        }).pipe(
          Effect.map((resp): LlmResult => ({
            text: (resp.choices?.[0]?.message?.content as string) ?? "",
            inToken: resp.usage?.promptTokens ?? 0,
            outToken: resp.usage?.completionTokens ?? 0,
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
            client.chat.stream({
              model: modelName,
              messages: [
                { role: "system", content: system },
                { role: "user", content: prompt },
              ],
              temperature: temp,
              maxTokens: maxOutput,
            }),
          catch: mapMistralError,
        }),
      ).pipe(
        Stream.flatMap((mistralStream) => {
          const iterator = mistralStream[Symbol.asyncIterator]();
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
                    catch: mapMistralError,
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
                  const delta = chunk.data?.choices?.[0]?.delta;
                  const content = delta?.content;
                  if (chunk.data?.usage !== undefined) {
                    totalInputTokens = chunk.data.usage.promptTokens ?? 0;
                    totalOutputTokens = chunk.data.usage.completionTokens ?? 0;
                  }
                  if (typeof content === "string" && content.length > 0) {
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

      return toAsyncGenerator(Stream.toAsyncIterable(stream), mapMistralError);
    },
  };
}

export type MistralProcessor = ReturnType<typeof makeMistralProcessor>;

export function makeMistralProcessor(
  config: MistralProcessorConfig,
): ReturnType<typeof makeLlmService> {
  return makeLlmService(config, makeMistralProvider(config));
}

export const MistralProcessor = makeMistralProcessor;

export const program = makeFlowProcessorProgram<ProcessorConfig, never, Llm>({
  id: "text-completion",
  specs: () => makeLlmSpecs(),
  layer: (config) =>
    Layer.succeed(
      Llm,
      Llm.of(makeLlmServiceShape(makeMistralProvider(config))),
    ),
});

const mistralTextCompletionRuntime = ManagedRuntime.make(Layer.empty);

export function run(): Promise<void> {
  return mistralTextCompletionRuntime.runPromise(program);
}

export function runMain(): void {
  NodeRuntime.runMain(program);
}
