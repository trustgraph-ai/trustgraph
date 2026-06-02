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
  tooManyRequestsError,
} from "@trustgraph/base";
import { Effect, Layer } from "effect";

export type AzureOpenAIProcessorConfig = ProcessorConfig & {
  model?: string;
  apiKey?: string;
  endpoint?: string;
  apiVersion?: string;
  temperature?: number;
  maxOutput?: number;
};

export function makeAzureOpenAIProvider(config: AzureOpenAIProcessorConfig): LlmProvider {
  const defaultModel = config.model ?? process.env.AZURE_MODEL ?? "gpt-4o";
  const defaultTemperature = config.temperature ?? 0.0;
  const maxOutput = config.maxOutput ?? 4096;

    const apiKey = config.apiKey ?? process.env.AZURE_TOKEN;
    if (apiKey === undefined || apiKey.length === 0) {
      throw new Error("Azure OpenAI API key not specified");
    }

    const endpoint = config.endpoint ?? process.env.AZURE_ENDPOINT;
    if (endpoint === undefined || endpoint.length === 0) {
      throw new Error("Azure OpenAI endpoint not specified");
    }

    const apiVersion =
      config.apiVersion ??
      process.env.AZURE_API_VERSION ??
      "2024-12-01-preview";

  const client = new AzureOpenAI({ apiKey, apiVersion, endpoint });

    console.log("[AzureOpenAI] LLM service initialized");

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
        const resp = await client.chat.completions.create({
          model: modelName,
          messages: [
            { role: "system", content: system },
            { role: "user", content: prompt },
          ],
          temperature: temp,
          max_completion_tokens: maxOutput,
        });

        return {
          text: resp.choices[0].message.content ?? "",
          inToken: resp.usage?.prompt_tokens ?? 0,
          outToken: resp.usage?.completion_tokens ?? 0,
          model: modelName,
        };
      } catch (err) {
        if ((err as any)?.status === 429) {
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
        const stream = await client.chat.completions.create({
          model: modelName,
          messages: [
            { role: "system", content: system },
            { role: "user", content: prompt },
          ],
          temperature: temp,
          max_completion_tokens: maxOutput,
          stream: true,
          stream_options: { include_usage: true },
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
      } catch (err) {
        if ((err as any)?.status === 429) {
          throw tooManyRequestsError();
        }
        throw err;
      }
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

export async function run(): Promise<void> {
  await Effect.runPromise(program);
}
