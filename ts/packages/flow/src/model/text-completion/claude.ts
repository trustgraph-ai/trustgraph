/**
 * Anthropic Claude text completion service.
 *
 * Python reference: trustgraph-flow/trustgraph/model/text_completion/claude/llm.py
 */

import { AnthropicClient, AnthropicLanguageModel } from "@effect/ai-anthropic";
import { NodeRuntime } from "@effect/platform-node";
import type {
  Llm,
  LlmProvider,
  ProcessorConfig,
} from "@trustgraph/base";
import {
  makeLlmService,
  makeFlowProcessorProgram,
  makeLlmSpecs,
} from "@trustgraph/base";
import { Context, Effect, Layer, Redacted } from "effect";
import { FetchHttpClient } from "effect/unstable/http";
import type {
  TextCompletionConfigError,
  TextCompletionRuntimeError,
} from "./common.ts";
import {
  makeLanguageModelProvider,
  makeTextCompletionLayer,
  optionalStringConfig,
  requiredString,
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

const loadClaudeConfig = Effect.fn("loadClaudeConfig")(function* (config: ClaudeProcessorConfig) {
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

const makeClaudeLayer = (apiKey: string) =>
  AnthropicClient.layer({
    apiKey: Redacted.make(apiKey),
  }).pipe(
    Layer.provide(FetchHttpClient.layer),
  );

export function makeClaudeProvider(
  config: ClaudeProcessorConfig,
): LlmProvider<TextCompletionRuntimeError> {
  const resolved = {
    defaultModel: config.model ?? "claude-sonnet-4-20250514",
    defaultTemperature: config.temperature ?? 0.0,
    maxOutput: config.maxOutput ?? 8192,
    apiKey: config.apiKey ?? "",
  } satisfies ResolvedClaudeConfig;
  return makeLanguageModelProvider({
    provider: "Claude",
    defaultModel: resolved.defaultModel,
    defaultTemperature: resolved.defaultTemperature,
    context: Context.empty(),
    makeLanguageModel: ({ model, temperature }) =>
      Effect.scoped(
        Layer.build(makeClaudeLayer(resolved.apiKey)).pipe(
          Effect.flatMap((context) =>
            AnthropicLanguageModel.make({
              model,
              config: {
                max_tokens: resolved.maxOutput,
                temperature,
              },
            }).pipe(Effect.provideContext(context))
          ),
        ),
      ),
  });
}

export const makeClaudeProviderEffect = Effect.fn("makeClaudeProvider")(function* (
  config: ClaudeProcessorConfig,
) {
  const resolved = yield* loadClaudeConfig(config);
  const context = yield* Layer.build(makeClaudeLayer(resolved.apiKey));

  yield* Effect.log("[Claude] LLM service initialized");
  return makeLanguageModelProvider({
    provider: "Claude",
    defaultModel: resolved.defaultModel,
    defaultTemperature: resolved.defaultTemperature,
    context,
    makeLanguageModel: ({ model, temperature }) =>
      AnthropicLanguageModel.make({
        model,
        config: {
          max_tokens: resolved.maxOutput,
          temperature,
        },
      }),
  });
});

export type ClaudeProcessor = ReturnType<typeof makeClaudeProcessor>;

export function makeClaudeProcessor(
  config: ClaudeProcessorConfig,
): ReturnType<typeof makeLlmService> {
  return makeLlmService(config, makeClaudeProvider(config));
}

export const ClaudeProcessor = makeClaudeProcessor;

export const program = makeFlowProcessorProgram<
  ClaudeProcessorConfig,
  TextCompletionConfigError | TextCompletionRuntimeError,
  Llm
>({
  id: "text-completion",
  specs: () => makeLlmSpecs(),
  layer: (config) => makeTextCompletionLayer(makeClaudeProviderEffect(config)),
});

export function runMain(): void {
  NodeRuntime.runMain(program);
}
