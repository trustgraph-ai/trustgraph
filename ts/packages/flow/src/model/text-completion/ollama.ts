/**
 * Ollama text completion service.
 *
 * Connects to a local Ollama instance for text generation.
 *
 * Python reference: trustgraph-flow/trustgraph/model/text_completion/ollama/llm.py
 */

import { Ollama } from "ollama";
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

export type OllamaProcessorConfig = ProcessorConfig & {
  model?: string;
  ollamaUrl?: string;
};

export function makeOllamaProvider(config: OllamaProcessorConfig): LlmProvider {
  const defaultModel =
      config.model ??
      process.env.OLLAMA_MODEL ??
      "qwen2.5:0.5b";

    const host =
      config.ollamaUrl ??
      process.env.OLLAMA_URL ??
      "http://localhost:11434";

  const client = new Ollama({ host });

    console.log(
    `[Ollama] LLM service initialized (host=${host}, model=${defaultModel})`,
    );

  return {
    generateContent: async (
      system: string,
      prompt: string,
      model?: string,
      _temperature?: number,
    ): Promise<LlmResult> => {
      const modelName = model ?? defaultModel;
      const fullPrompt = system + "\n\n" + prompt;

      const resp = await client.generate({
        model: modelName,
        prompt: fullPrompt,
        stream: false,
      });

      return {
        text: resp.response,
        inToken: resp.prompt_eval_count ?? 0,
        outToken: resp.eval_count ?? 0,
        model: modelName,
      };
    },
    supportsStreaming: () => true,
    generateContentStream: async function* (
      system: string,
      prompt: string,
      model?: string,
      _temperature?: number,
    ): AsyncGenerator<LlmChunk> {
      const modelName = model ?? defaultModel;
      const fullPrompt = system + "\n\n" + prompt;

      const stream = await client.generate({
        model: modelName,
        prompt: fullPrompt,
        stream: true,
      });

      let totalInputTokens = 0;
      let totalOutputTokens = 0;

      for await (const chunk of stream) {
      // Token counts accumulate across chunks; keep the latest values
        if (chunk.prompt_eval_count !== undefined) {
          totalInputTokens = chunk.prompt_eval_count;
        }
        if (chunk.eval_count !== undefined) {
          totalOutputTokens = chunk.eval_count;
        }

        if (chunk.response.length > 0) {
          yield {
            text: chunk.response,
            inToken: null,
            outToken: null,
            model: modelName,
            isFinal: false,
          };
        }
      }

    // Final chunk with accumulated token counts
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

export type OllamaProcessor = ReturnType<typeof makeOllamaProcessor>;

export function makeOllamaProcessor(config: OllamaProcessorConfig): ReturnType<typeof makeLlmService> {
  return makeLlmService(config, makeOllamaProvider(config));
}

export const OllamaProcessor = makeOllamaProcessor;

export const program = makeFlowProcessorProgram<ProcessorConfig, never, Llm>({
  id: "text-completion",
  specs: () => makeLlmSpecs(),
  layer: (config) =>
    Layer.succeed(
      Llm,
      Llm.of(makeLlmServiceShape(makeOllamaProvider(config))),
    ),
});

export async function run(): Promise<void> {
  await Effect.runPromise(program);
}
