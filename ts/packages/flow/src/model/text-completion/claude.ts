/**
 * Anthropic Claude text completion service.
 *
 * Python reference: trustgraph-flow/trustgraph/model/text_completion/claude/llm.py
 */

import Anthropic from "@anthropic-ai/sdk";
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
  llmStreamPart,
  optionalStringConfig,
  providerStatusError,
  requiredString,
  streamTextCompletionChunks,
  toAsyncGenerator,
  type TextCompletionRuntimeError,
} from "./common.ts";

export type ClaudeProcessorConfig = ProcessorConfig & {
  model?: string;
  apiKey?: string;
  temperature?: number;
  maxOutput?: number;
};

type ResolvedClaudeConfig = {
  readonly defaultModel: string;
  readonly defaultTemperature: number;
  readonly maxOutput: number;
  readonly apiKey: string;
};

const loadClaudeConfig = Effect.fn("loadClaudeConfig")(function*(config: ClaudeProcessorConfig) {
    const apiKey = yield* requiredString(
      config.apiKey ?? (yield* optionalStringConfig("Claude", "CLAUDE_KEY")),
      "Claude",
      "CLAUDE_KEY",
      "Claude API key not specified",
    );

    return {
      defaultModel: config.model ?? "claude-sonnet-4-20250514",
      defaultTemperature: config.temperature ?? 0.0,
      maxOutput: config.maxOutput ?? 8192,
      apiKey,
    } satisfies ResolvedClaudeConfig;
});

const mapClaudeError = (error: unknown): TextCompletionRuntimeError =>
  providerStatusError("Claude", error);

export function makeClaudeProvider(config: ClaudeProcessorConfig): LlmProvider {
  const {
    defaultModel,
    defaultTemperature,
    maxOutput,
    apiKey,
  } = Effect.runSync(loadClaudeConfig(config)) satisfies ResolvedClaudeConfig;

  const client = new Anthropic({ apiKey });

  Effect.runSync(Effect.log("[Claude] LLM service initialized"));

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
            client.messages.create({
              model: modelName,
              max_tokens: maxOutput,
              temperature: temp,
              system,
              messages: [
                { role: "user", content: prompt },
              ],
            }),
          catch: mapClaudeError,
        }).pipe(
          Effect.map((response): LlmResult => {
            const firstContent = response.content[0];
            const text = firstContent?.type === "text"
              ? firstContent.text
              : "";

            return {
              text,
              inToken: response.usage.input_tokens,
              outToken: response.usage.output_tokens,
              model: modelName,
            };
          }),
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
        Effect.try({
          try: () =>
            client.messages.stream({
              model: modelName,
              max_tokens: maxOutput,
              temperature: temp,
              system,
              messages: [
                { role: "user", content: prompt },
              ],
            }),
          catch: mapClaudeError,
        }),
      ).pipe(
        Stream.flatMap((anthropicStream) =>
          streamTextCompletionChunks(anthropicStream, {
            model: modelName,
            mapError: mapClaudeError,
            extract: (event) =>
              event.type === "content_block_delta" && event.delta.type === "text_delta"
                ? llmStreamPart({ text: event.delta.text })
                : llmStreamPart({}),
            finalTokens: Effect.tryPromise({
              try: () => anthropicStream.finalMessage(),
              catch: mapClaudeError,
            }).pipe(
              Effect.map((finalMessage) => ({
                inToken: finalMessage.usage.input_tokens,
                outToken: finalMessage.usage.output_tokens,
              })),
            ),
          })
        ),
      );

      return toAsyncGenerator(Stream.toAsyncIterable(stream), mapClaudeError);
    },
  };
}

export type ClaudeProcessor = ReturnType<typeof makeClaudeProcessor>;

export function makeClaudeProcessor(
  config: ClaudeProcessorConfig,
): ReturnType<typeof makeLlmService> {
  return makeLlmService(config, makeClaudeProvider(config));
}

export const ClaudeProcessor = makeClaudeProcessor;

export const program = makeFlowProcessorProgram<ProcessorConfig, never, Llm>({
  id: "text-completion",
  specs: () => makeLlmSpecs(),
  layer: (config) =>
    Layer.succeed(
      Llm,
      Llm.of(makeLlmServiceShape(makeClaudeProvider(config))),
    ),
});

const claudeTextCompletionRuntime = ManagedRuntime.make(Layer.empty);

export function run(): Promise<void> {
  return claudeTextCompletionRuntime.runPromise(program);
}

export function runMain(): void {
  NodeRuntime.runMain(program);
}
