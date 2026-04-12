/**
 * Ollama embeddings service.
 *
 * Simple HTTP POST to a local Ollama instance to generate embeddings.
 * Extends EmbeddingsService from @trustgraph/base so it plugs into the
 * flow processor framework (consumer/producer wiring is handled by the base class).
 *
 * Python reference: trustgraph-flow/trustgraph/embeddings/ollama/processor.py
 */

import {
  EmbeddingsService,
  type ProcessorConfig,
} from "@trustgraph/base";

export interface OllamaEmbeddingsConfig extends ProcessorConfig {
  model?: string;
  ollamaHost?: string;
}

interface OllamaEmbedResponse {
  embeddings: number[][];
}

export class OllamaEmbeddingsProcessor extends EmbeddingsService {
  private defaultModel: string;
  private ollamaHost: string;

  constructor(config: OllamaEmbeddingsConfig) {
    super(config);

    this.defaultModel = config.model ?? "mxbai-embed-large";
    this.ollamaHost =
      config.ollamaHost ??
      process.env.OLLAMA_URL ??
      process.env.OLLAMA_HOST ??
      "http://localhost:11434";

    console.log(
      `[OllamaEmbeddings] Initialized (host=${this.ollamaHost}, model=${this.defaultModel})`,
    );
  }

  async onEmbeddings(texts: string[], model?: string): Promise<number[][]> {
    if (!texts || texts.length === 0) {
      return [];
    }

    const useModel = model ?? this.defaultModel;

    const url = `${this.ollamaHost}/api/embed`;

    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: useModel,
        input: texts,
      }),
    });

    if (!response.ok) {
      const body = await response.text();
      throw new Error(
        `Ollama embeddings request failed (${response.status}): ${body}`,
      );
    }

    const data = (await response.json()) as OllamaEmbedResponse;

    return data.embeddings;
  }
}

export async function run(): Promise<void> {
  await OllamaEmbeddingsProcessor.launch("embeddings");
}
