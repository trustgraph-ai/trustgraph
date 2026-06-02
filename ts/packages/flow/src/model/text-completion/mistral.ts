/**
 * Mistral text completion service.
 *
 * Env:
 *   MISTRAL_TOKEN (required – Mistral API key)
 *   MISTRAL_MODEL (default: ministral-8b-latest)
 */

import { Mistral } from "@mistralai/mistralai";
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

export type MistralProcessorConfig = ProcessorConfig & {
  model?: string;
  apiKey?: string;
  temperature?: number;
  maxOutput?: number;
};

export function makeMistralProvider(config: MistralProcessorConfig): LlmProvider {
  const defaultModel =
    config.model ?? process.env.MISTRAL_MODEL ?? "ministral-8b-latest";
  const defaultTemperature = config.temperature ?? 0.0;
  const maxOutput = config.maxOutput ?? 4096;
    const apiKey = config.apiKey ?? process.env.MISTRAL_TOKEN;
    if (apiKey === undefined || apiKey.length === 0) {
      throw new Error("Mistral API key not specified");
    }

  const client = new Mistral({ apiKey });

    console.log("[Mistral] LLM service initialized");

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
        const resp = await client.chat.complete({
          model: modelName,
          messages: [
            { role: "system", content: system },
            { role: "user", content: prompt },
          ],
          temperature: temp,
          maxTokens: maxOutput,
        });

        return {
          text: (resp.choices?.[0]?.message?.content as string) ?? "",
          inToken: resp.usage?.promptTokens ?? 0,
          outToken: resp.usage?.completionTokens ?? 0,
          model: modelName,
        };
      } catch (err) {
        if ((err as any)?.statusCode === 429 || (err as any)?.status === 429) {
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
        const stream = await client.chat.stream({
          model: modelName,
          messages: [
            { role: "system", content: system },
            { role: "user", content: prompt },
          ],
          temperature: temp,
          maxTokens: maxOutput,
        });

        let totalInputTokens = 0;
        let totalOutputTokens = 0;

        for await (const chunk of stream) {
          const delta = chunk.data?.choices?.[0]?.delta;
          const content = delta?.content;
          if (typeof content === "string" && content.length > 0) {
            yield {
              text: content,
              inToken: null,
              outToken: null,
              model: modelName,
              isFinal: false,
            };
          }

          if (chunk.data?.usage !== undefined) {
            totalInputTokens = chunk.data.usage.promptTokens ?? 0;
            totalOutputTokens = chunk.data.usage.completionTokens ?? 0;
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
        if ((err as any)?.statusCode === 429 || (err as any)?.status === 429) {
          throw tooManyRequestsError();
        }
        throw err;
      }
    },
  };
}

export type MistralProcessor = ReturnType<typeof makeMistralProcessor>;

export function makeMistralProcessor(config: MistralProcessorConfig): ReturnType<typeof makeLlmService> {
  return makeLlmService(config, makeMistralProvider(config));
}

export const MistralProcessor = makeMistralProcessor;

export const program = makeFlowProcessorProgram<ProcessorConfig, never, Llm>({
  id: "text-completion",
  specs: () => makeLlmSpecs(),
  layer: (config) =>
    Layer.succeed(
      Llm,
      Llm.of(makeLlmServiceShape(makeMistralProvider(config))),
    ),
});

export async function run(): Promise<void> {
  await Effect.runPromise(program);
}
