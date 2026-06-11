/**
 * Qdrant document embeddings query service.
 *
 * Input: vector, user, collection, limit
 * Output: list of { chunkId, score } matches
 *
 * Python reference: trustgraph-flow/trustgraph/query/doc_embeddings/qdrant/service.py
 */

import { errorMessage } from "@trustgraph/base";
import { Config, Context, Effect, Layer } from "effect";
import * as O from "effect/Option";
import * as S from "effect/Schema";
import type { QdrantClientFactory, QdrantClientLike } from "../../qdrant/client.js";
import { makeQdrantClient, } from "../../qdrant/client.js";

export interface QdrantDocQueryConfig {
  url?: string;
  apiKey?: string;
  clientFactory?: QdrantClientFactory;
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
    cause: S.Defect({ includeStack: true }),
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

const DocPointPayloadSchema = S.Struct({
  chunk_id: S.String,
  content: S.optionalKey(S.String),
});

const decodeDocPointPayload = (payload: unknown) =>
  S.decodeUnknownEffect(DocPointPayloadSchema)(payload).pipe(Effect.option);

export interface QdrantDocEmbeddingsQuery {
  readonly query: (
    request: DocEmbeddingsQueryRequest,
  ) => Effect.Effect<ReadonlyArray<ChunkMatch>, QdrantDocEmbeddingsQueryError>;
}

const makeQdrantDocEmbeddingsQueryClient = (
  config: QdrantDocQueryConfig,
  resolved: ResolvedQdrantDocQueryConfig,
) =>
  Effect.try({
    try: () =>
      makeQdrantClient(config.clientFactory, {
        url: resolved.url,
        ...(resolved.apiKey !== undefined ? { apiKey: resolved.apiKey } : {}),
      }),
    catch: (cause) => qdrantDocEmbeddingsQueryError("create-client", cause),
  });

const makeQdrantDocEmbeddingsQueryFromClient = (
  client: QdrantClientLike,
): QdrantDocEmbeddingsQueryServiceShape => {
  const queryImpl = Effect.fn("QdrantDocEmbeddingsQuery.query")(function* (request: DocEmbeddingsQueryRequest) {
    const { vector, user, collection, limit } = request;

    if (vector.length === 0) {
      return [];
    }

    const dim = vector.length;
    const collectionName = `d_${user}_${collection}_${dim}`;

    // Check if collection exists -- return empty if not
    const exists = yield* client.collectionExists(collectionName).pipe(
      Effect.mapError((cause) => qdrantDocEmbeddingsQueryError("collection-exists", cause)),
    );
    if (!exists.exists) {
      yield* Effect.log(
        `[QdrantDocQuery] Collection ${collectionName} does not exist, returning empty results`,
      );
      return [];
    }

    const searchResult = yield* client.search(
      collectionName,
      {
        vector,
        limit,
        with_payload: true,
      },
    ).pipe(
      Effect.mapError((cause) => qdrantDocEmbeddingsQueryError("search", cause)),
    );

    const chunks: ChunkMatch[] = [];
    for (const point of searchResult) {
      const payload = yield* decodeDocPointPayload(point.payload);
      if (O.isNone(payload)) continue;

      const chunkId = payload.value.chunk_id;
      if (chunkId.length === 0) continue;

      chunks.push({
        chunkId,
        score: point.score,
        ...(payload.value.content !== undefined ? { content: payload.value.content } : {}),
      });
    }

    return chunks;
  });

  return {
    query: queryImpl,
  };
};

export const makeQdrantDocEmbeddingsQueryServiceEffect = Effect.fn(
  "makeQdrantDocEmbeddingsQueryServiceEffect",
)(function* (config: QdrantDocQueryConfig = {}) {
  const resolved = yield* loadQdrantDocQueryConfig(config).pipe(
    Effect.mapError((cause) => qdrantDocEmbeddingsQueryError("load-config", cause)),
  );
  const client = yield* makeQdrantDocEmbeddingsQueryClient(config, resolved);
  yield* Effect.log("[QdrantDocQuery] Query service initialized");
  return makeQdrantDocEmbeddingsQueryFromClient(client);
});

const withQdrantDocEmbeddingsQuery = <A>(
  config: QdrantDocQueryConfig,
  use: (query: QdrantDocEmbeddingsQueryServiceShape) => Effect.Effect<A, QdrantDocEmbeddingsQueryError>,
) =>
  makeQdrantDocEmbeddingsQueryServiceEffect(config).pipe(
    Effect.flatMap(use),
  );

export function makeQdrantDocEmbeddingsQuery(
  config: QdrantDocQueryConfig = {},
): QdrantDocEmbeddingsQuery {
  return {
    query: (request) => withQdrantDocEmbeddingsQuery(config, (query) => query.query(request)),
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
): QdrantDocEmbeddingsQueryServiceShape => ({
  query: (request) => withQdrantDocEmbeddingsQuery(config, (query) => query.query(request)),
});

export const QdrantDocEmbeddingsQueryLive = (
  config: QdrantDocQueryConfig = {},
): Layer.Layer<QdrantDocEmbeddingsQueryService, QdrantDocEmbeddingsQueryError> =>
  Layer.effect(
    QdrantDocEmbeddingsQueryService,
    makeQdrantDocEmbeddingsQueryServiceEffect(config).pipe(
      Effect.map((service) => QdrantDocEmbeddingsQueryService.of(service)),
    ),
  );
