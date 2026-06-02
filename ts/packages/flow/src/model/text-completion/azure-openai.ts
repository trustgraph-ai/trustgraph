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
import { NodeRuntime } from "@effect/platform-node";
import {
  makeLlmService,
  makeFlowProcessorProgram,
  makeLlmSpecs,
  type Llm,
  type LlmProvider,
  type ProcessorConfig,
  type LlmResult,
  type LlmChunk,
} from "@trustgraph/base";
import { Effect, Layer, ManagedRuntime, Stream } from "effect";
import {
  llmStreamPart,
  makeTextCompletionLayer,
  optionalStringConfig,
  providerStatusError,
  requiredString,
  streamTextCompletionChunks,
  toAsyncGenerator,
  type TextCompletionConfigError,
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
    } satisfies ResolvedAzureOpenAIConfig;
});

const mapAzureOpenAIError = (error: unknown): TextCompletionRuntimeError =>
  providerStatusError("AzureOpenAI", error);

const makeAzureOpenAIProviderFromClient = (
  resolved: ResolvedAzureOpenAIConfig,
  client: AzureOpenAI,
): LlmProvider => {
  const {
    defaultModel,
    defaultTemperature,
    maxOutput,
  } = resolved;

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
        Stream.flatMap((openAIStream) =>
          streamTextCompletionChunks(openAIStream, {
            model: modelName,
            mapError: mapAzureOpenAIError,
            extract: (chunk) =>
              llmStreamPart({
                text: chunk.choices[0]?.delta?.content,
                inToken: chunk.usage?.prompt_tokens,
                outToken: chunk.usage?.completion_tokens,
              }),
          })
        ),
      );

      return toAsyncGenerator(Stream.toAsyncIterable(stream), mapAzureOpenAIError);
    },
  } satisfies LlmProvider;
};

export function makeAzureOpenAIProvider(config: AzureOpenAIProcessorConfig): LlmProvider {
  return Effect.runSync(makeAzureOpenAIProviderEffect(config));
}

export const makeAzureOpenAIProviderEffect = Effect.fn("makeAzureOpenAIProvider")(function*(
  config: AzureOpenAIProcessorConfig,
) {
  const resolved = yield* loadAzureOpenAIConfig(config);
  const client = yield* Effect.try({
    try: () =>
      new AzureOpenAI({
        apiKey: resolved.apiKey,
        apiVersion: resolved.apiVersion,
        endpoint: resolved.endpoint,
      }),
    catch: mapAzureOpenAIError,
  });

  yield* Effect.log("[AzureOpenAI] LLM service initialized");
  return makeAzureOpenAIProviderFromClient(resolved, client);
});

export type AzureOpenAIProcessor = ReturnType<typeof makeAzureOpenAIProcessor>;

export function makeAzureOpenAIProcessor(
  config: AzureOpenAIProcessorConfig,
): ReturnType<typeof makeLlmService> {
  return makeLlmService(config, makeAzureOpenAIProvider(config));
}

export const AzureOpenAIProcessor = makeAzureOpenAIProcessor;

export const program = makeFlowProcessorProgram<
  AzureOpenAIProcessorConfig,
  TextCompletionConfigError | TextCompletionRuntimeError,
  Llm
>({
  id: "text-completion",
  specs: () => makeLlmSpecs(),
  layer: (config) => makeTextCompletionLayer(makeAzureOpenAIProviderEffect(config)),
});

const azureOpenAITextCompletionRuntime = ManagedRuntime.make(Layer.empty);

export function run(): Promise<void> {
  return azureOpenAITextCompletionRuntime.runPromise(program);
}

export function runMain(): void {
  NodeRuntime.runMain(program);
}
