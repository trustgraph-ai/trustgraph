/**
 * Ollama embeddings provider.
 *
 * Python reference: trustgraph-flow/trustgraph/embeddings/ollama/processor.py
 */

import { Config, Effect, Layer } from "effect";
import * as O from "effect/Option";
import * as S from "effect/Schema";
import {
  Embeddings,
  EmbeddingsError,
  errorMessage,
  makeEmbeddingsService,
  makeEmbeddingsSpecs,
  type EmbeddingsServiceShape,
  type ProcessorConfig,
} from "@trustgraph/base";
import { makeFlowProcessorProgram } from "@trustgraph/base";

export interface OllamaEmbeddingsConfig extends ProcessorConfig {
  model?: string;
  ollamaHost?: string;
  fetch?: typeof fetch;
}

const EmbeddingVector = S.Array(S.Number);

const OllamaEmbedResponse = S.Struct({
  embeddings: S.Array(EmbeddingVector),
});

type OllamaEmbedResponse = typeof OllamaEmbedResponse.Type;

interface ResolvedOllamaEmbeddingsConfig {
  readonly defaultModel: string;
  readonly ollamaHost: string;
  readonly fetchImpl: typeof fetch;
}

const ollamaEmbeddingsError = (operation: string, cause: unknown): EmbeddingsError =>
  EmbeddingsError.make({
    operation,
    message: errorMessage(cause),
    provider: "ollama",
  });

const ollamaEmbeddingsMessageError = (operation: string, message: string): EmbeddingsError =>
  EmbeddingsError.make({
    operation,
    message,
    provider: "ollama",
  });

const optionalStringConfig = Effect.fn("OllamaEmbeddings.optionalStringConfig")(function*(name: string) {
  return O.getOrUndefined(yield* Config.string(name).pipe(Config.option));
});

const loadOllamaEmbeddingsConfig = Effect.fn("OllamaEmbeddings.loadConfig")(function*(
  config: OllamaEmbeddingsConfig,
) {
  return {
    defaultModel: config.model ?? "mxbai-embed-large",
    ollamaHost:
      config.ollamaHost ??
      (yield* optionalStringConfig("OLLAMA_URL")) ??
      (yield* optionalStringConfig("OLLAMA_HOST")) ??
      "http://localhost:11434",
    fetchImpl: config.fetch ?? globalThis.fetch,
  } satisfies ResolvedOllamaEmbeddingsConfig;
});

export function makeOllamaEmbeddings(config: OllamaEmbeddingsConfig): EmbeddingsServiceShape {
  const {
    defaultModel,
    ollamaHost,
    fetchImpl,
  } = Effect.runSync(loadOllamaEmbeddingsConfig(config)) satisfies ResolvedOllamaEmbeddingsConfig;

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
          Effect.mapError((error) => ollamaEmbeddingsError("ollama.encode-request", error))
        );

        const response = yield* Effect.tryPromise({
          try: () =>
            fetchImpl(url, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body,
            }),
          catch: (error) => ollamaEmbeddingsError("ollama.fetch", error),
        });

        if (!response.ok) {
          const errorBody = yield* Effect.tryPromise({
            try: () => response.text(),
            catch: (error) => ollamaEmbeddingsError("ollama.error-body", error),
          });
          return yield* ollamaEmbeddingsMessageError(
            "ollama.embed",
            `Ollama embeddings request failed (${response.status}): ${errorBody}`,
          );
        }

        const data = yield* Effect.tryPromise({
          try: () => response.json() as Promise<unknown>,
          catch: (error) => ollamaEmbeddingsError("ollama.response-json", error),
        });
        const decoded = yield* S.decodeUnknownEffect(OllamaEmbedResponse)(data).pipe(
          Effect.mapError((error) => ollamaEmbeddingsError("ollama.decode-response", error))
        );
        return Array.from(decoded.embeddings, (vector) => Array.from(vector));
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

export type OllamaEmbeddingsProcessor = ReturnType<typeof makeOllamaEmbeddingsProcessor>;

export function makeOllamaEmbeddingsProcessor(config: OllamaEmbeddingsConfig) {
  const embeddings = makeOllamaEmbeddings(config);
  const resolved = Effect.runSync(loadOllamaEmbeddingsConfig(config)) satisfies ResolvedOllamaEmbeddingsConfig;
  Effect.runSync(Effect.log(
    `[OllamaEmbeddings] Initialized (host=${resolved.ollamaHost}, model=${resolved.defaultModel})`,
  ));
  return makeEmbeddingsService(config, embeddings);
}

export const OllamaEmbeddingsProcessor = makeOllamaEmbeddingsProcessor;

export const program = makeFlowProcessorProgram<OllamaEmbeddingsConfig, never, Embeddings>({
  id: "embeddings",
  specs: () => makeEmbeddingsSpecs(),
  layer: (config) => OllamaEmbeddingsLive(config),
});

export function run(): Promise<void> {
  return Effect.runPromise(program);
}
