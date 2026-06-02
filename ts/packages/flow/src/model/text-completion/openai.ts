/**
 * OpenAI text completion service.
 *
 * Python reference: trustgraph-flow/trustgraph/model/text_completion/openai/llm.py
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

export function makeOpenAIProvider(config: OpenAIProcessorConfig): LlmProvider {
  const {
    defaultModel,
    defaultTemperature,
    maxOutput,
    apiKey,
    baseURL,
  } = Effect.runSync(loadOpenAIConfig(config)) satisfies ResolvedOpenAIConfig;

  const client = new OpenAI({
    apiKey,
    baseURL,
  });

  Effect.runSync(Effect.log("[OpenAI] LLM service initialized"));

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
          catch: mapOpenAIError,
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
          catch: mapOpenAIError,
        }),
      ).pipe(
        Stream.flatMap((openAIStream) => {
          const iterator = openAIStream[Symbol.asyncIterator]();
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
                    catch: mapOpenAIError,
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

      return toAsyncGenerator(Stream.toAsyncIterable(stream), mapOpenAIError);
    },
  };
}

export type OpenAIProcessor = ReturnType<typeof makeOpenAIProcessor>;

export function makeOpenAIProcessor(
  config: OpenAIProcessorConfig,
): ReturnType<typeof makeLlmService> {
  return makeLlmService(config, makeOpenAIProvider(config));
}

export const OpenAIProcessor = makeOpenAIProcessor;

export const program = makeFlowProcessorProgram<ProcessorConfig, never, Llm>({
  id: "text-completion",
  specs: () => makeLlmSpecs(),
  layer: (config) =>
    Layer.succeed(
      Llm,
      Llm.of(makeLlmServiceShape(makeOpenAIProvider(config))),
    ),
});

const openAITextCompletionRuntime = ManagedRuntime.make(Layer.empty);

export function run(): Promise<void> {
  return openAITextCompletionRuntime.runPromise(program);
}

export function runMain(): void {
  NodeRuntime.runMain(program);
}
