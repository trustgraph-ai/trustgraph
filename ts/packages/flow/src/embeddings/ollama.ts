/**
 * Ollama embeddings provider.
 *
 * Python reference: trustgraph-flow/trustgraph/embeddings/ollama/processor.py
 */

import { Effect, Layer } from "effect";
import * as S from "effect/Schema";
import {
  Embeddings,
  EmbeddingsService,
  embeddingsError,
  type EmbeddingsServiceShape,
  type ProcessorConfig,
} from "@trustgraph/base";
import { makeProcessorProgram } from "@trustgraph/base";

export interface OllamaEmbeddingsConfig extends ProcessorConfig {
  model?: string;
  ollamaHost?: string;
  fetch?: typeof fetch;
}

interface OllamaEmbedResponse {
  embeddings: number[][];
}

export function makeOllamaEmbeddings(config: OllamaEmbeddingsConfig): EmbeddingsServiceShape {
  const defaultModel = config.model ?? "mxbai-embed-large";
  const ollamaHost =
    config.ollamaHost ??
    process.env.OLLAMA_URL ??
    process.env.OLLAMA_HOST ??
    "http://localhost:11434";
  const fetchImpl = config.fetch ?? globalThis.fetch;

  return {
    embed: Effect.fn("OllamaEmbeddings.embed")((texts: ReadonlyArray<string>, model?: string) => {
      if (texts.length === 0) {
        return Effect.succeed([]);
      }

      const useModel = model ?? defaultModel;
      const url = `${ollamaHost}/api/embed`;

      return Effect.gen(function* () {
        const body = yield* S.encodeUnknownEffect(S.UnknownFromJsonString)({
          model: useModel,
          input: Array.from(texts),
        }).pipe(
          Effect.mapError((error) => embeddingsError("ollama.encode-request", error, "ollama")),
        );

        return yield* Effect.tryPromise({
          try: async () => {
            const response = await fetchImpl(url, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body,
            });

            if (!response.ok) {
              const errorBody = await response.text();
              throw new Error(
                `Ollama embeddings request failed (${response.status}): ${errorBody}`,
              );
            }

            const data = (await response.json()) as OllamaEmbedResponse;
            return data.embeddings;
          },
          catch: (error) => embeddingsError("ollama.embed", error, "ollama"),
        });
      });
    }),
  };
}

export function OllamaEmbeddingsLive(config: OllamaEmbeddingsConfig): Layer.Layer<Embeddings> {
  return Layer.succeed(
    Embeddings,
    Embeddings.of(makeOllamaEmbeddings(config)),
  );
}

export class OllamaEmbeddingsProcessor extends EmbeddingsService {
  private readonly embeddings: EmbeddingsServiceShape;

  constructor(config: OllamaEmbeddingsConfig) {
    super(config);
    this.embeddings = makeOllamaEmbeddings(config);

    console.log(
      `[OllamaEmbeddings] Initialized (host=${config.ollamaHost ?? process.env.OLLAMA_URL ?? process.env.OLLAMA_HOST ?? "http://localhost:11434"}, model=${config.model ?? "mxbai-embed-large"})`,
    );
  }

  override startEffect() {
    return super.startEffect().pipe(
      Effect.provideService(Embeddings, Embeddings.of(this.embeddings)),
    );
  }
}

export const program = makeProcessorProgram({
  id: "embeddings",
  make: (config) => new OllamaEmbeddingsProcessor(config),
});

export async function run(): Promise<void> {
  await OllamaEmbeddingsProcessor.launch("embeddings");
}
