/**
 * OpenAI text completion service.
 *
 * Python reference: trustgraph-flow/trustgraph/model/text_completion/openai/llm.py
 */

import OpenAI from "openai";
import { NodeRuntime } from "@effect/platform-node";
import type {
  Llm,
  LlmProvider,
  ProcessorConfig,
  LlmResult,
} from "@trustgraph/base";
import {
  makeLlmService,
  makeFlowProcessorProgram,
  makeLlmSpecs,
} from "@trustgraph/base";
import { Effect, Stream } from "effect";
import type {
  TextCompletionConfigError,
  TextCompletionRuntimeError,
} from "./common.ts";
import {
  llmStreamPart,
  makeTextCompletionLayer,
  optionalStringConfig,
  providerStatusError,
  requiredString,
  streamTextCompletionChunks,
} from "./common.ts";

export type OpenAIProcessorConfig = ProcessorConfig & {
  model?: string;
  apiKey?: string;
  baseUrl?: string;
  temperature?: number;
  maxOutput?: number;
};

type ResolvedOpenAIConfig = {
  readonly defaultModel: string;
  readonly defaultTemperature: number;
  readonly maxOutput: number;
  readonly apiKey: string;
  readonly baseURL: string | undefined;
};

const loadOpenAIConfig = Effect.fn("loadOpenAIConfig")(function*(config: OpenAIProcessorConfig) {
    const apiKey = yield* requiredString(
      config.apiKey ?? (yield* optionalStringConfig("OpenAI", "OPENAI_TOKEN")),
      "OpenAI",
      "OPENAI_TOKEN",
      "OpenAI API key not specified",
    );

    return {
      defaultModel: config.model ?? "gpt-4o",
      defaultTemperature: config.temperature ?? 0.0,
      maxOutput: config.maxOutput ?? 4096,
      apiKey,
      baseURL: config.baseUrl ?? (yield* optionalStringConfig("OpenAI", "OPENAI_BASE_URL")),
    } satisfies ResolvedOpenAIConfig;
});

const mapOpenAIError = (error: unknown): TextCompletionRuntimeError =>
  providerStatusError("OpenAI", error);

const makeOpenAIProviderFromClient = (
  resolved: ResolvedOpenAIConfig,
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
            max_completion_tokens: maxOutput,
          }),
        catch: mapOpenAIError,
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
              max_completion_tokens: maxOutput,
              stream: true,
              stream_options: { include_usage: true },
            }),
          catch: mapOpenAIError,
        }),
      ).pipe(
        Stream.flatMap((openAIStream) =>
          streamTextCompletionChunks(openAIStream, {
            model: modelName,
            mapError: mapOpenAIError,
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

export function makeOpenAIProvider(
  config: OpenAIProcessorConfig,
): LlmProvider<TextCompletionRuntimeError> {
  return Effect.runSync(makeOpenAIProviderEffect(config));
}

export const makeOpenAIProviderEffect = Effect.fn("makeOpenAIProvider")(function*(
  config: OpenAIProcessorConfig,
) {
  const resolved = yield* loadOpenAIConfig(config);
  const client = yield* Effect.try({
    try: () =>
      new OpenAI({
        apiKey: resolved.apiKey,
        baseURL: resolved.baseURL,
      }),
    catch: mapOpenAIError,
  });

  yield* Effect.log("[OpenAI] LLM service initialized");
  return makeOpenAIProviderFromClient(resolved, client);
});

export type OpenAIProcessor = ReturnType<typeof makeOpenAIProcessor>;

export function makeOpenAIProcessor(
  config: OpenAIProcessorConfig,
): ReturnType<typeof makeLlmService> {
  return makeLlmService(config, makeOpenAIProvider(config));
}

export const OpenAIProcessor = makeOpenAIProcessor;

export const program = makeFlowProcessorProgram<
  OpenAIProcessorConfig,
  TextCompletionConfigError | TextCompletionRuntimeError,
  Llm
>({
  id: "text-completion",
  specs: () => makeLlmSpecs(),
  layer: (config) => makeTextCompletionLayer(makeOpenAIProviderEffect(config)),
});

export function runMain(): void {
  NodeRuntime.runMain(program);
}
