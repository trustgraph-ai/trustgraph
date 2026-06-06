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
  type TextCompletionConfigError,
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

const makeOpenAICompatibleProviderFromClient = (
  resolved: ResolvedOpenAICompatibleConfig,
  client: OpenAI,
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
        Stream.flatMap((openAIStream) =>
          streamTextCompletionChunks(openAIStream, {
            model: modelName,
            mapError: mapOpenAICompatibleError,
            extract: (chunk) =>
              llmStreamPart({
                text: chunk.choices[0]?.delta?.content,
                inToken: chunk.usage?.prompt_tokens,
                outToken: chunk.usage?.completion_tokens,
              }),
          })
        ),
      );
    },
  } satisfies LlmProvider<TextCompletionRuntimeError>;
};

export function makeOpenAICompatibleProvider(
  config: OpenAICompatibleProcessorConfig,
): LlmProvider<TextCompletionRuntimeError> {
  return Effect.runSync(makeOpenAICompatibleProviderEffect(config));
}

export const makeOpenAICompatibleProviderEffect = Effect.fn("makeOpenAICompatibleProvider")(function*(
  config: OpenAICompatibleProcessorConfig,
) {
  const resolved = yield* loadOpenAICompatibleConfig(config);
  const client = yield* Effect.try({
    try: () => new OpenAI({ baseURL: resolved.baseURL, apiKey: resolved.apiKey }),
    catch: mapOpenAICompatibleError,
  });

  yield* Effect.log("[OpenAI-Compatible] LLM service initialized");
  return makeOpenAICompatibleProviderFromClient(resolved, client);
});

export type OpenAICompatibleProcessor = ReturnType<typeof makeOpenAICompatibleProcessor>;

export function makeOpenAICompatibleProcessor(
  config: OpenAICompatibleProcessorConfig,
): ReturnType<typeof makeLlmService> {
  return makeLlmService(config, makeOpenAICompatibleProvider(config));
}

export const OpenAICompatibleProcessor = makeOpenAICompatibleProcessor;

export const program = makeFlowProcessorProgram<
  OpenAICompatibleProcessorConfig,
  TextCompletionConfigError | TextCompletionRuntimeError,
  Llm
>({
  id: "text-completion",
  specs: () => makeLlmSpecs(),
  layer: (config) => makeTextCompletionLayer(makeOpenAICompatibleProviderEffect(config)),
});

export function runMain(): void {
  NodeRuntime.runMain(program);
}
