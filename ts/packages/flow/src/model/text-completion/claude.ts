/**
 * Anthropic Claude text completion service.
 *
 * Python reference: trustgraph-flow/trustgraph/model/text_completion/claude/llm.py
 */

import Anthropic from "@anthropic-ai/sdk";
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
  tooManyRequestsError,
} from "@trustgraph/base";
import { Effect, Layer } from "effect";

export type ClaudeProcessorConfig = ProcessorConfig & {
  model?: string;
  apiKey?: string;
  temperature?: number;
  maxOutput?: number;
};

export function makeClaudeProvider(config: ClaudeProcessorConfig): LlmProvider {
  const defaultModel = config.model ?? "claude-sonnet-4-20250514";
  const defaultTemperature = config.temperature ?? 0.0;
  const maxOutput = config.maxOutput ?? 8192;
    const apiKey = config.apiKey ?? process.env.CLAUDE_KEY;
    if (apiKey === undefined || apiKey.length === 0) {
      throw new Error("Claude API key not specified");
    }

  const client = new Anthropic({ apiKey });

    console.log("[Claude] LLM service initialized");

  return {
    generateContent: async (
      system: string,
      prompt: string,
      model?: string,
      temperature?: number,
    ): Promise<LlmResult> => {
      const modelName = model ?? defaultModel;
      const temp = temperature ?? defaultTemperature;

      try {
        const response = await client.messages.create({
          model: modelName,
          max_tokens: maxOutput,
          temperature: temp,
          system,
          messages: [
            { role: "user", content: prompt },
          ],
        });

        const text = response.content[0].type === "text"
          ? response.content[0].text
          : "";

        return {
          text,
          inToken: response.usage.input_tokens,
          outToken: response.usage.output_tokens,
          model: modelName,
        };
      } catch (err) {
        if (err instanceof Anthropic.RateLimitError) {
          throw tooManyRequestsError();
        }
        throw err;
      }
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

      try {
        const stream = client.messages.stream({
          model: modelName,
          max_tokens: maxOutput,
          temperature: temp,
          system,
          messages: [
            { role: "user", content: prompt },
          ],
        });

        for await (const event of stream) {
          if (event.type === "content_block_delta" && event.delta.type === "text_delta") {
            yield {
              text: event.delta.text,
              inToken: null,
              outToken: null,
              model: modelName,
              isFinal: false,
            };
          }
        }

        const finalMessage = await stream.finalMessage();
        yield {
          text: "",
          inToken: finalMessage.usage.input_tokens,
          outToken: finalMessage.usage.output_tokens,
          model: modelName,
          isFinal: true,
        };
      } catch (err) {
        if (err instanceof Anthropic.RateLimitError) {
          throw tooManyRequestsError();
        }
        throw err;
      }
    },
  };
}

export type ClaudeProcessor = ReturnType<typeof makeClaudeProcessor>;

export function makeClaudeProcessor(config: ClaudeProcessorConfig): ReturnType<typeof makeLlmService> {
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

export async function run(): Promise<void> {
  await Effect.runPromise(program);
}
