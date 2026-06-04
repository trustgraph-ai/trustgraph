/**
 * Ollama embeddings provider.
 *
 * Python reference: trustgraph-flow/trustgraph/embeddings/ollama/processor.py
 */

import { NodeRuntime } from "@effect/platform-node";
import { Config, Effect, Layer, ManagedRuntime } from "effect";
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

const responseJson = (response: Response): Promise<unknown> =>
  response.json();

const makeOllamaEmbeddingsFromConfig = ({
  defaultModel,
  ollamaHost,
  fetchImpl,
}: ResolvedOllamaEmbeddingsConfig): EmbeddingsServiceShape => ({
    embed: Effect.fn("OllamaEmbeddings.embed")(function* (texts: ReadonlyArray<string>, model?: string) {
      if (texts.length === 0) {
        return [];
      }

      const useModel = model ?? defaultModel;
      const url = `${ollamaHost}/api/embed`;

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
        try: () => responseJson(response),
        catch: (error) => ollamaEmbeddingsError("ollama.response-json", error),
      });
      const decoded = yield* S.decodeUnknownEffect(OllamaEmbedResponse)(data).pipe(
        Effect.mapError((error) => ollamaEmbeddingsError("ollama.decode-response", error))
      );
      return Array.from(decoded.embeddings, (vector) => Array.from(vector));
    }),
  });

export const makeOllamaEmbeddingsEffect = Effect.fn("makeOllamaEmbeddingsEffect")(function* (
  config: OllamaEmbeddingsConfig,
) {
  const resolved = yield* loadOllamaEmbeddingsConfig(config).pipe(
    Effect.mapError((cause) => ollamaEmbeddingsError("ollama.load-config", cause)),
  );
  yield* Effect.log(
    `[OllamaEmbeddings] Initialized (host=${resolved.ollamaHost}, model=${resolved.defaultModel})`,
  );
  return makeOllamaEmbeddingsFromConfig(resolved);
});

export function makeOllamaEmbeddings(config: OllamaEmbeddingsConfig): EmbeddingsServiceShape {
  return Effect.runSync(makeOllamaEmbeddingsEffect(config));
}

export function OllamaEmbeddingsLive(config: OllamaEmbeddingsConfig): Layer.Layer<Embeddings, EmbeddingsError> {
  return Layer.effect(
    Embeddings,
    makeOllamaEmbeddingsEffect(config).pipe(
      Effect.map((embeddings) => Embeddings.of(embeddings)),
    ),
  );
}

export type OllamaEmbeddingsProcessor = ReturnType<typeof makeOllamaEmbeddingsProcessor>;

export function makeOllamaEmbeddingsProcessor(config: OllamaEmbeddingsConfig) {
  const embeddings = makeOllamaEmbeddings(config);
  return makeEmbeddingsService(config, embeddings);
}

export const OllamaEmbeddingsProcessor = makeOllamaEmbeddingsProcessor;

export const program = makeFlowProcessorProgram<OllamaEmbeddingsConfig, EmbeddingsError, Embeddings>({
  id: "embeddings",
  specs: () => makeEmbeddingsSpecs(),
  layer: (config) => OllamaEmbeddingsLive(config),
});

const ollamaEmbeddingsRuntime = ManagedRuntime.make(Layer.empty);

export function run(): Promise<void> {
  return ollamaEmbeddingsRuntime.runPromise(program);
}

export function runMain(): void {
  NodeRuntime.runMain(program);
}
