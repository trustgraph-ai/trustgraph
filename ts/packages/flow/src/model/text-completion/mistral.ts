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
  providerStatusError,
  requiredString,
  streamTextCompletionChunks,
  textFromContent,
  type TextCompletionConfigError,
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

const makeMistralProviderFromClient = (
  resolved: ResolvedMistralConfig,
  client: Mistral,
): LlmProvider<TextCompletionRuntimeError> => {
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
    ) => {
      const modelName = model ?? defaultModel;
      const temp = temperature ?? defaultTemperature;

      return Effect.tryPromise({
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
          text: textFromContent(resp.choices?.[0]?.message?.content),
          inToken: resp.usage?.promptTokens ?? 0,
          outToken: resp.usage?.completionTokens ?? 0,
          model: modelName,
        })),
      );
    },
    supportsStreaming: () => true,
    generateContentStream: (
      system: string,
      prompt: string,
      model?: string,
      temperature?: number,
    ) => {
      const modelName = model ?? defaultModel;
      const temp = temperature ?? defaultTemperature;

      return Stream.fromEffect(
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
        Stream.flatMap((mistralStream) =>
          streamTextCompletionChunks(mistralStream, {
            model: modelName,
            mapError: mapMistralError,
            extract: (chunk) =>
              llmStreamPart({
                text: textFromContent(chunk.data?.choices?.[0]?.delta?.content),
                inToken: chunk.data?.usage?.promptTokens,
                outToken: chunk.data?.usage?.completionTokens,
              }),
          })
        ),
      );
    },
  } satisfies LlmProvider<TextCompletionRuntimeError>;
};

export function makeMistralProvider(
  config: MistralProcessorConfig,
): LlmProvider<TextCompletionRuntimeError> {
  return Effect.runSync(makeMistralProviderEffect(config));
}

export const makeMistralProviderEffect = Effect.fn("makeMistralProvider")(function*(
  config: MistralProcessorConfig,
) {
  const resolved = yield* loadMistralConfig(config);
  const client = yield* Effect.try({
    try: () => new Mistral({ apiKey: resolved.apiKey }),
    catch: mapMistralError,
  });

  yield* Effect.log("[Mistral] LLM service initialized");
  return makeMistralProviderFromClient(resolved, client);
});

export type MistralProcessor = ReturnType<typeof makeMistralProcessor>;

export function makeMistralProcessor(
  config: MistralProcessorConfig,
): ReturnType<typeof makeLlmService> {
  return makeLlmService(config, makeMistralProvider(config));
}

export const MistralProcessor = makeMistralProcessor;

export const program = makeFlowProcessorProgram<
  MistralProcessorConfig,
  TextCompletionConfigError | TextCompletionRuntimeError,
  Llm
>({
  id: "text-completion",
  specs: () => makeLlmSpecs(),
  layer: (config) => makeTextCompletionLayer(makeMistralProviderEffect(config)),
});

export function runMain(): void {
  NodeRuntime.runMain(program);
}
