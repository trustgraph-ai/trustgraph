/**
 * Azure OpenAI text completion service.
 *
 * Env:
 *   AZURE_TOKEN       (required – Azure OpenAI API key)
 *   AZURE_ENDPOINT    (required – e.g. https://my-resource.openai.azure.com)
 *   AZURE_MODEL       (default: gpt-4o)
 *   AZURE_API_VERSION (default: 2024-12-01-preview)
 */

import { AzureOpenAI } from "openai";
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
import { Effect, Layer, Stream } from "effect";
import {
  optionalStringConfig,
  providerStatusError,
  requiredString,
  toAsyncGenerator,
  type TextCompletionRuntimeError,
} from "./common.ts";

export type AzureOpenAIProcessorConfig = ProcessorConfig & {
  model?: string;
  apiKey?: string;
  endpoint?: string;
  apiVersion?: string;
  temperature?: number;
  maxOutput?: number;
};

type ResolvedAzureOpenAIConfig = {
  readonly defaultModel: string;
  readonly defaultTemperature: number;
  readonly maxOutput: number;
  readonly apiKey: string;
  readonly endpoint: string;
  readonly apiVersion: string;
};

const loadAzureOpenAIConfig = Effect.fn("loadAzureOpenAIConfig")(function* (
  config: AzureOpenAIProcessorConfig,
) {
    const defaultModel =
      config.model ?? (yield* optionalStringConfig("AzureOpenAI", "AZURE_MODEL")) ?? "gpt-4o";
    const apiKey = yield* requiredString(
      config.apiKey ?? (yield* optionalStringConfig("AzureOpenAI", "AZURE_TOKEN")),
      "AzureOpenAI",
      "AZURE_TOKEN",
      "Azure OpenAI API key not specified",
    );
    const endpoint = yield* requiredString(
      config.endpoint ?? (yield* optionalStringConfig("AzureOpenAI", "AZURE_ENDPOINT")),
      "AzureOpenAI",
      "AZURE_ENDPOINT",
      "Azure OpenAI endpoint not specified",
    );
    const apiVersion =
      config.apiVersion ??
      (yield* optionalStringConfig("AzureOpenAI", "AZURE_API_VERSION")) ??
      "2024-12-01-preview";

    return {
      defaultModel,
      defaultTemperature: config.temperature ?? 0.0,
      maxOutput: config.maxOutput ?? 4096,
      apiKey,
      endpoint,
      apiVersion,
    };
});

const mapAzureOpenAIError = (error: unknown): TextCompletionRuntimeError =>
  providerStatusError("AzureOpenAI", error);

export function makeAzureOpenAIProvider(config: AzureOpenAIProcessorConfig): LlmProvider {
  const {
    defaultModel,
    defaultTemperature,
    maxOutput,
    apiKey,
    endpoint,
    apiVersion,
  } = Effect.runSync(loadAzureOpenAIConfig(config)) satisfies ResolvedAzureOpenAIConfig;
  const client = new AzureOpenAI({ apiKey, apiVersion, endpoint });

  Effect.runSync(Effect.log("[AzureOpenAI] LLM service initialized"));

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
              max_completion_tokens: maxOutput,
            }),
          catch: mapAzureOpenAIError,
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
              max_completion_tokens: maxOutput,
              stream: true,
              stream_options: { include_usage: true },
            }),
          catch: mapAzureOpenAIError,
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
                    catch: mapAzureOpenAIError,
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

      return toAsyncGenerator(Stream.toAsyncIterable(stream), mapAzureOpenAIError);
    },
  };
}

export type AzureOpenAIProcessor = ReturnType<typeof makeAzureOpenAIProcessor>;

export function makeAzureOpenAIProcessor(
  config: AzureOpenAIProcessorConfig,
): ReturnType<typeof makeLlmService> {
  return makeLlmService(config, makeAzureOpenAIProvider(config));
}

export const AzureOpenAIProcessor = makeAzureOpenAIProcessor;

export const program = makeFlowProcessorProgram<ProcessorConfig, never, Llm>({
  id: "text-completion",
  specs: () => makeLlmSpecs(),
  layer: (config) =>
    Layer.succeed(
      Llm,
      Llm.of(makeLlmServiceShape(makeAzureOpenAIProvider(config))),
    ),
});

export function run(): Promise<void> {
  return Effect.runPromise(program);
}
