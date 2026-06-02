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

import { QdrantClient } from "@qdrant/js-client-rest";
import { errorMessage, type Term } from "@trustgraph/base";
import { Config, Context, Effect, Layer } from "effect";
import * as O from "effect/Option";
import * as S from "effect/Schema";

export interface QdrantGraphQueryConfig {
  url?: string;
  apiKey?: string;
}

export interface EntityMatch {
  entity: Term;
  score: number;
}

export interface GraphEmbeddingsQueryRequest {
  vector: number[];
  user: string;
  collection: string;
  limit: number;
}

export class QdrantGraphEmbeddingsQueryError extends S.TaggedErrorClass<QdrantGraphEmbeddingsQueryError>()(
  "QdrantGraphEmbeddingsQueryError",
  {
    message: S.String,
    operation: S.String,
    cause: S.DefectWithStack,
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

export interface QdrantGraphEmbeddingsQuery {
  readonly query: (request: GraphEmbeddingsQueryRequest) => Promise<EntityMatch[]>;
  readonly queryEffect: (
    request: GraphEmbeddingsQueryRequest,
  ) => Effect.Effect<ReadonlyArray<EntityMatch>, QdrantGraphEmbeddingsQueryError>;
}

export function makeQdrantGraphEmbeddingsQuery(
  config: QdrantGraphQueryConfig = {},
): QdrantGraphEmbeddingsQuery {
  const resolved = Effect.runSync(loadQdrantGraphQueryConfig(config));

  const client = new QdrantClient({
    url: resolved.url,
    ...(resolved.apiKey !== undefined ? { apiKey: resolved.apiKey } : {}),
  });

  Effect.runSync(Effect.log("[QdrantGraphQuery] Query service initialized"));

  const queryEffect = Effect.fn("QdrantGraphEmbeddingsQuery.query")(function* (
    request: GraphEmbeddingsQueryRequest,
  ) {
    const { vector, user, collection, limit } = request;

    if (vector.length === 0) {
      return [];
    }

    const dim = vector.length;
    const collectionName = `t_${user}_${collection}_${dim}`;

    // Check if collection exists -- return empty if not
    const exists = yield* Effect.tryPromise({
      try: () => client.collectionExists(collectionName),
      catch: (cause) => qdrantGraphEmbeddingsQueryError("collection-exists", cause),
    });
    if (!exists.exists) {
      yield* Effect.log(
        `[QdrantGraphQuery] Collection ${collectionName} does not exist, returning empty results`,
      );
      return [];
    }

    // Query 2x the limit so we have a better chance of getting `limit`
    // unique entities after deduplication (same heuristic as Python impl)
    const searchResult = yield* Effect.tryPromise({
      try: () =>
        client.search(collectionName, {
          vector,
          limit: limit * 2,
          with_payload: true,
        }),
      catch: (cause) => qdrantGraphEmbeddingsQueryError("search", cause),
    });

    const entitySet = new Set<string>();
    const entities: EntityMatch[] = [];

    for (const point of searchResult) {
      const payload = point.payload as Record<string, unknown> | undefined;
      const entityValue = payload?.entity as string | undefined;
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
    query: (request) => Effect.runPromise(queryEffect(request)),
    queryEffect,
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
): QdrantGraphEmbeddingsQueryServiceShape => {
  const query = makeQdrantGraphEmbeddingsQuery(config);
  return {
    query: query.queryEffect,
  };
};

export const QdrantGraphEmbeddingsQueryLive = (
  config: QdrantGraphQueryConfig = {},
): Layer.Layer<QdrantGraphEmbeddingsQueryService> =>
  Layer.succeed(
    QdrantGraphEmbeddingsQueryService,
    QdrantGraphEmbeddingsQueryService.of(makeQdrantGraphEmbeddingsQueryService(config)),
  );
