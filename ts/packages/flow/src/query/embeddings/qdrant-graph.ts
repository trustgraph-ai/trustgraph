/**
 * Qdrant graph embeddings query service.
 *
 * Input: vector, user, collection, limit
 * Output: list of Term entities with scores, deduplicated by entity value
 *
 * Queries limit*2 points and deduplicates by entity value to ensure
 * we return up to `limit` unique entities.
 *
 * Python reference: trustgraph-flow/trustgraph/query/graph_embeddings/qdrant/service.py
 */

import { Term, errorMessage } from "@trustgraph/base";
import { Config, Context, Effect, Layer } from "effect";
import * as O from "effect/Option";
import * as S from "effect/Schema";
import type { QdrantClientFactory, QdrantClientLike } from "../../qdrant/client.js";
import { makeQdrantClient, } from "../../qdrant/client.js";

export interface QdrantGraphQueryConfig {
  url?: string;
  apiKey?: string;
  clientFactory?: QdrantClientFactory;
}

export class EntityMatch extends S.Class<EntityMatch>("EntityMatch")({
  entity: Term,
  score: S.Finite,
}, { description: "A scored graph-entity match from embeddings query." }) {}

export class GraphEmbeddingsQueryRequest extends S.Class<GraphEmbeddingsQueryRequest>("GraphEmbeddingsQueryRequest")({
  vector: S.Array(S.Finite),
  user: S.String,
  collection: S.String,
  limit: S.Finite,
}, { description: "Graph embeddings similarity query request." }) {}

export class QdrantGraphEmbeddingsQueryError extends S.TaggedErrorClass<QdrantGraphEmbeddingsQueryError>()(
  "QdrantGraphEmbeddingsQueryError",
  {
    message: S.String,
    operation: S.String,
    cause: S.Defect({ includeStack: true }),
  },
) {}

const qdrantGraphEmbeddingsQueryError = (operation: string, cause: unknown) =>
  QdrantGraphEmbeddingsQueryError.make({
    operation,
    message: errorMessage(cause),
    cause,
  });

interface ResolvedQdrantGraphQueryConfig {
  readonly url: string;
  readonly apiKey?: string;
}

const loadQdrantGraphQueryConfig = Effect.fn("QdrantGraphEmbeddingsQuery.loadConfig")(function* (
  config: QdrantGraphQueryConfig,
) {
  const envApiKey = O.getOrUndefined(yield* Config.string("QDRANT_API_KEY").pipe(Config.option));
  const apiKey = config.apiKey ?? envApiKey;
  return {
    url: config.url ?? (yield* Config.string("QDRANT_URL").pipe(Config.withDefault("http://localhost:6333"))),
    ...(apiKey !== undefined && apiKey.length > 0 ? { apiKey } : {}),
  } satisfies ResolvedQdrantGraphQueryConfig;
});

function createTerm(value: string): Term {
  if (value.startsWith("http://") || value.startsWith("https://")) {
    return { type: "IRI", iri: value };
  }
  return { type: "LITERAL", value };
}

const GraphPointPayloadSchema = S.Struct({
  entity: S.String,
});

const decodeGraphPointPayload = (payload: unknown) =>
  S.decodeUnknownEffect(GraphPointPayloadSchema)(payload).pipe(Effect.option);

export interface QdrantGraphEmbeddingsQuery {
  readonly query: (
    request: GraphEmbeddingsQueryRequest,
  ) => Effect.Effect<ReadonlyArray<EntityMatch>, QdrantGraphEmbeddingsQueryError>;
}

const makeQdrantGraphEmbeddingsQueryClient = (
  config: QdrantGraphQueryConfig,
  resolved: ResolvedQdrantGraphQueryConfig,
) =>
  Effect.try({
    try: () =>
      makeQdrantClient(config.clientFactory, {
        url: resolved.url,
        ...(resolved.apiKey !== undefined ? { apiKey: resolved.apiKey } : {}),
      }),
    catch: (cause) => qdrantGraphEmbeddingsQueryError("create-client", cause),
  });

const makeQdrantGraphEmbeddingsQueryFromClient = (
  client: QdrantClientLike,
): QdrantGraphEmbeddingsQueryServiceShape => {

  const queryImpl = Effect.fn("QdrantGraphEmbeddingsQuery.query")(function* (
    request: GraphEmbeddingsQueryRequest,
  ) {
    const { vector, user, collection, limit } = request;

    if (vector.length === 0) {
      return [];
    }

    const dim = vector.length;
    const collectionName = `t_${user}_${collection}_${dim}`;

    // Check if collection exists -- return empty if not
    const exists = yield* client.collectionExists(collectionName).pipe(
      Effect.mapError((cause) => qdrantGraphEmbeddingsQueryError("collection-exists", cause)),
    );
    if (!exists.exists) {
      yield* Effect.log(
        `[QdrantGraphQuery] Collection ${collectionName} does not exist, returning empty results`,
      );
      return [];
    }

    // Query 2x the limit so we have a better chance of getting `limit`
    // unique entities after deduplication (same heuristic as Python impl)
    const searchResult = yield* client.search(
      collectionName,
      {
        vector,
        limit: limit * 2,
        with_payload: true,
      },
    ).pipe(
      Effect.mapError((cause) => qdrantGraphEmbeddingsQueryError("search", cause)),
    );

    const entitySet = new Set<string>();
    const entities: EntityMatch[] = [];

    for (const point of searchResult) {
      const payload = yield* decodeGraphPointPayload(point.payload);
      if (O.isNone(payload)) continue;

      const entityValue = payload.value.entity;
      if (entityValue === undefined || entityValue.length === 0) continue;

      // Deduplicate by entity value, keeping the highest score (results are
      // already sorted by score descending from Qdrant)
      if (!entitySet.has(entityValue)) {
        entitySet.add(entityValue);
        entities.push({
          entity: createTerm(entityValue),
          score: point.score,
        });
      }

      // Stop once we have enough unique entities
      if (entities.length >= limit) break;
    }

    return entities;
  });

  return {
    query: queryImpl,
  };
};

export const makeQdrantGraphEmbeddingsQueryServiceEffect = Effect.fn(
  "makeQdrantGraphEmbeddingsQueryServiceEffect",
)(function* (config: QdrantGraphQueryConfig = {}) {
  const resolved = yield* loadQdrantGraphQueryConfig(config).pipe(
    Effect.mapError((cause) => qdrantGraphEmbeddingsQueryError("load-config", cause)),
  );
  const client = yield* makeQdrantGraphEmbeddingsQueryClient(config, resolved);
  yield* Effect.log("[QdrantGraphQuery] Query service initialized");
  return makeQdrantGraphEmbeddingsQueryFromClient(client);
});

const withQdrantGraphEmbeddingsQuery = <A>(
  config: QdrantGraphQueryConfig,
  use: (query: QdrantGraphEmbeddingsQueryServiceShape) => Effect.Effect<A, QdrantGraphEmbeddingsQueryError>,
) =>
  makeQdrantGraphEmbeddingsQueryServiceEffect(config).pipe(
    Effect.flatMap(use),
  );

export function makeQdrantGraphEmbeddingsQuery(
  config: QdrantGraphQueryConfig = {},
): QdrantGraphEmbeddingsQuery {
  return {
    query: (request) => withQdrantGraphEmbeddingsQuery(config, (query) => query.query(request)),
  };
}

export interface QdrantGraphEmbeddingsQueryServiceShape {
  readonly query: (
    request: GraphEmbeddingsQueryRequest,
  ) => Effect.Effect<ReadonlyArray<EntityMatch>, QdrantGraphEmbeddingsQueryError>;
}

export class QdrantGraphEmbeddingsQueryService extends Context.Service<
  QdrantGraphEmbeddingsQueryService,
  QdrantGraphEmbeddingsQueryServiceShape
>()(
  "@trustgraph/flow/query/embeddings/qdrant-graph/QdrantGraphEmbeddingsQueryService",
) {}

export const makeQdrantGraphEmbeddingsQueryService = (
  config: QdrantGraphQueryConfig = {},
): QdrantGraphEmbeddingsQueryServiceShape => ({
  query: (request) => withQdrantGraphEmbeddingsQuery(config, (query) => query.query(request)),
});

export const QdrantGraphEmbeddingsQueryLive = (
  config: QdrantGraphQueryConfig = {},
): Layer.Layer<QdrantGraphEmbeddingsQueryService, QdrantGraphEmbeddingsQueryError> =>
  Layer.effect(
    QdrantGraphEmbeddingsQueryService,
    makeQdrantGraphEmbeddingsQueryServiceEffect(config).pipe(
      Effect.map((service) => QdrantGraphEmbeddingsQueryService.of(service)),
    ),
  );
