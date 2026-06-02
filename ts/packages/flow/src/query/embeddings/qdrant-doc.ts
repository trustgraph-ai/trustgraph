/**
 * Qdrant document embeddings query service.
 *
 * Input: vector, user, collection, limit
 * Output: list of { chunkId, score } matches
 *
 * Python reference: trustgraph-flow/trustgraph/query/doc_embeddings/qdrant/service.py
 */

import { QdrantClient } from "@qdrant/js-client-rest";
import { errorMessage } from "@trustgraph/base";
import { Config, Context, Effect, Layer } from "effect";
import * as O from "effect/Option";
import * as S from "effect/Schema";

export interface QdrantDocQueryConfig {
  url?: string;
  apiKey?: string;
}

export interface ChunkMatch {
  chunkId: string;
  score: number;
  content?: string;
}

export interface DocEmbeddingsQueryRequest {
  vector: number[];
  user: string;
  collection: string;
  limit: number;
}

export class QdrantDocEmbeddingsQueryError extends S.TaggedErrorClass<QdrantDocEmbeddingsQueryError>()(
  "QdrantDocEmbeddingsQueryError",
  {
    message: S.String,
    operation: S.String,
    cause: S.DefectWithStack,
  },
) {}

const qdrantDocEmbeddingsQueryError = (operation: string, cause: unknown) =>
  QdrantDocEmbeddingsQueryError.make({
    operation,
    message: errorMessage(cause),
    cause,
  });

interface ResolvedQdrantDocQueryConfig {
  readonly url: string;
  readonly apiKey?: string;
}

const loadQdrantDocQueryConfig = Effect.fn("QdrantDocEmbeddingsQuery.loadConfig")(function* (
  config: QdrantDocQueryConfig,
) {
  const envApiKey = O.getOrUndefined(yield* Config.string("QDRANT_API_KEY").pipe(Config.option));
  const apiKey = config.apiKey ?? envApiKey;
  return {
    url: config.url ?? (yield* Config.string("QDRANT_URL").pipe(Config.withDefault("http://localhost:6333"))),
    ...(apiKey !== undefined && apiKey.length > 0 ? { apiKey } : {}),
  } satisfies ResolvedQdrantDocQueryConfig;
});

export interface QdrantDocEmbeddingsQuery {
  readonly query: (request: DocEmbeddingsQueryRequest) => Promise<ChunkMatch[]>;
  readonly queryEffect: (
    request: DocEmbeddingsQueryRequest,
  ) => Effect.Effect<ReadonlyArray<ChunkMatch>, QdrantDocEmbeddingsQueryError>;
}

export function makeQdrantDocEmbeddingsQuery(
  config: QdrantDocQueryConfig = {},
): QdrantDocEmbeddingsQuery {
  const resolved = Effect.runSync(loadQdrantDocQueryConfig(config));

  const client = new QdrantClient({
    url: resolved.url,
    ...(resolved.apiKey !== undefined ? { apiKey: resolved.apiKey } : {}),
  });

  Effect.runSync(Effect.log("[QdrantDocQuery] Query service initialized"));

  const queryEffect = Effect.fn("QdrantDocEmbeddingsQuery.query")(function* (request: DocEmbeddingsQueryRequest) {
    const { vector, user, collection, limit } = request;

    if (vector.length === 0) {
      return [];
    }

    const dim = vector.length;
    const collectionName = `d_${user}_${collection}_${dim}`;

    // Check if collection exists -- return empty if not
    const exists = yield* Effect.tryPromise({
      try: () => client.collectionExists(collectionName),
      catch: (cause) => qdrantDocEmbeddingsQueryError("collection-exists", cause),
    });
    if (!exists.exists) {
      yield* Effect.log(
        `[QdrantDocQuery] Collection ${collectionName} does not exist, returning empty results`,
      );
      return [];
    }

    const searchResult = yield* Effect.tryPromise({
      try: () =>
        client.search(collectionName, {
          vector,
          limit,
          with_payload: true,
        }),
      catch: (cause) => qdrantDocEmbeddingsQueryError("search", cause),
    });

    const chunks: ChunkMatch[] = [];
    for (const point of searchResult) {
      const payload = point.payload as Record<string, unknown> | undefined;
      const chunkId = payload?.chunk_id as string | undefined;
      if (chunkId !== undefined && chunkId.length > 0) {
        chunks.push({
          chunkId,
          score: point.score,
          ...(typeof payload?.content === "string" ? { content: payload.content } : {}),
        });
      }
    }

    return chunks;
  });

  return {
    query: (request) => Effect.runPromise(queryEffect(request)),
    queryEffect,
  };
}

export interface QdrantDocEmbeddingsQueryServiceShape {
  readonly query: (
    request: DocEmbeddingsQueryRequest,
  ) => Effect.Effect<ReadonlyArray<ChunkMatch>, QdrantDocEmbeddingsQueryError>;
}

export class QdrantDocEmbeddingsQueryService extends Context.Service<
  QdrantDocEmbeddingsQueryService,
  QdrantDocEmbeddingsQueryServiceShape
>()(
  "@trustgraph/flow/query/embeddings/qdrant-doc/QdrantDocEmbeddingsQueryService",
) {}

export const makeQdrantDocEmbeddingsQueryService = (
  config: QdrantDocQueryConfig = {},
): QdrantDocEmbeddingsQueryServiceShape => {
  const query = makeQdrantDocEmbeddingsQuery(config);
  return {
    query: query.queryEffect,
  };
};

export const QdrantDocEmbeddingsQueryLive = (
  config: QdrantDocQueryConfig = {},
): Layer.Layer<QdrantDocEmbeddingsQueryService> =>
  Layer.succeed(
    QdrantDocEmbeddingsQueryService,
    QdrantDocEmbeddingsQueryService.of(makeQdrantDocEmbeddingsQueryService(config)),
  );
