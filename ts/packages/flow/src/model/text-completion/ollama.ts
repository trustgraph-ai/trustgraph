/**
 * Ollama text completion service.
 *
 * Connects to a local Ollama instance for text generation.
 *
 * Python reference: trustgraph-flow/trustgraph/model/text_completion/ollama/llm.py
 */

import { Ollama } from "ollama";
import { LlmService, type ProcessorConfig, type LlmResult, type LlmChunk } from "@trustgraph/base";
import { makeProcessorProgram } from "@trustgraph/base";

export class OllamaProcessor extends LlmService {
  private client: Ollama;
  private readonly defaultModel: string;

  constructor(config: ProcessorConfig & {
    model?: string;
    ollamaUrl?: string;
  }) {
    super(config);

    this.defaultModel =
      config.model ??
      process.env.OLLAMA_MODEL ??
      "qwen2.5:0.5b";

    const host =
      config.ollamaUrl ??
      process.env.OLLAMA_URL ??
      "http://localhost:11434";

    this.client = new Ollama({ host });

    console.log(
      `[Ollama] LLM service initialized (host=${host}, model=${this.defaultModel})`,
    );
  }

  async generateContent(
    system: string,
    prompt: string,
    model?: string,
    _temperature?: number,
  ): Promise<LlmResult> {
    const modelName = model ?? this.defaultModel;
    const fullPrompt = system + "\n\n" + prompt;

    const resp = await this.client.generate({
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
  }

  override supportsStreaming(): boolean {
    return true;
  }

  async *generateContentStream(
    system: string,
    prompt: string,
    model?: string,
    _temperature?: number,
  ): AsyncGenerator<LlmChunk> {
    const modelName = model ?? this.defaultModel;
    const fullPrompt = system + "\n\n" + prompt;

    const stream = await this.client.generate({
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
  }
}

export const program = makeProcessorProgram({
  id: "text-completion",
  make: (config) => new OllamaProcessor(config),
});

export async function run(): Promise<void> {
  await OllamaProcessor.launch("text-completion");
}
