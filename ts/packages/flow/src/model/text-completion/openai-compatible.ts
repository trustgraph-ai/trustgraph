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
import { Effect, Layer } from "effect";

export type OpenAICompatibleProcessorConfig = ProcessorConfig & {
  model?: string;
  apiKey?: string;
  baseUrl?: string;
  temperature?: number;
  maxOutput?: number;
};

export function makeOpenAICompatibleProvider(
  config: OpenAICompatibleProcessorConfig,
): LlmProvider {
  const defaultModel =
    config.model ?? process.env.OPENAI_COMPAT_MODEL ?? "default";
  const defaultTemperature = config.temperature ?? 0.0;
  const maxOutput = config.maxOutput ?? 4096;

    const baseURL = config.baseUrl ?? process.env.OPENAI_COMPAT_URL;
    if (baseURL === undefined || baseURL.length === 0) {
      throw new Error(
        "OpenAI-compatible server URL not specified (set OPENAI_COMPAT_URL)",
      );
    }

    const apiKey =
      config.apiKey ?? process.env.OPENAI_COMPAT_KEY ?? "sk-no-key-required";

  const client = new OpenAI({ baseURL, apiKey });

    console.log("[OpenAI-Compatible] LLM service initialized");

  return {
    generateContent: async (
      system: string,
      prompt: string,
      model?: string,
      temperature?: number,
    ): Promise<LlmResult> => {
      const modelName = model ?? defaultModel;
      const temp = temperature ?? defaultTemperature;

      const resp = await client.chat.completions.create({
        model: modelName,
        messages: [
          { role: "system", content: system },
          { role: "user", content: prompt },
        ],
        temperature: temp,
        max_tokens: maxOutput,
      });

      return {
        text: resp.choices[0].message.content ?? "",
        inToken: resp.usage?.prompt_tokens ?? 0,
        outToken: resp.usage?.completion_tokens ?? 0,
        model: modelName,
      };
    },
    supportsStreaming: () => true,
    generateContentStream: async function* (
      system: string,
      prompt: string,
      model?: string,
      temperature?: number,
    ): AsyncGenerator<LlmChunk> {
      const modelName = model ?? defaultModel;
      const temp = temperature ?? defaultTemperature;

      const stream = await client.chat.completions.create({
        model: modelName,
        messages: [
          { role: "system", content: system },
          { role: "user", content: prompt },
        ],
        temperature: temp,
        max_tokens: maxOutput,
        stream: true,
      });

      let totalInputTokens = 0;
      let totalOutputTokens = 0;

      for await (const chunk of stream) {
        const content = chunk.choices[0]?.delta?.content;
        if (content !== null && content !== undefined && content.length > 0) {
          yield {
            text: content,
            inToken: null,
            outToken: null,
            model: modelName,
            isFinal: false,
          };
        }

        if (chunk.usage !== null && chunk.usage !== undefined) {
          totalInputTokens = chunk.usage.prompt_tokens;
          totalOutputTokens = chunk.usage.completion_tokens;
        }
      }

      yield {
        text: "",
        inToken: totalInputTokens,
        outToken: totalOutputTokens,
        model: modelName,
        isFinal: true,
      };
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

export async function run(): Promise<void> {
  await Effect.runPromise(program);
}
