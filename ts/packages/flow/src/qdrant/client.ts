import { QdrantClient, type QdrantClientParams } from "@qdrant/js-client-rest";
import { errorMessage } from "@trustgraph/base";
import { Effect } from "effect";
import * as S from "effect/Schema";

export interface QdrantCollectionStatus {
  readonly exists: boolean;
}

export interface QdrantCollectionDescription {
  readonly name: string;
}

export interface QdrantCollections {
  readonly collections: ReadonlyArray<QdrantCollectionDescription>;
}

export interface QdrantScoredPoint {
  readonly score: number;
  readonly payload?: unknown;
}

export class QdrantClientError extends S.TaggedErrorClass<QdrantClientError>()("QdrantClientError", {
  message: S.String,
  operation: S.String,
  cause: S.Defect({ includeStack: true }),
}) {}

const qdrantClientError = (operation: string, cause: unknown) =>
  QdrantClientError.make({
    operation,
    message: errorMessage(cause),
    cause,
  });

export interface QdrantClientLike {
  readonly collectionExists: (collectionName: string) => Effect.Effect<QdrantCollectionStatus, QdrantClientError>;
  readonly createCollection: (
    collectionName: string,
    options: {
      readonly vectors: {
        readonly size: number;
        readonly distance: "Cosine";
      };
    },
  ) => Effect.Effect<void, QdrantClientError>;
  readonly upsert: (
    collectionName: string,
    options: {
      readonly points: ReadonlyArray<{
        readonly id: string;
        readonly vector: ReadonlyArray<number>;
        readonly payload?: Record<string, unknown>;
      }>;
    },
  ) => Effect.Effect<void, QdrantClientError>;
  readonly getCollections: Effect.Effect<QdrantCollections, QdrantClientError>;
  readonly deleteCollection: (collectionName: string) => Effect.Effect<void, QdrantClientError>;
  readonly search: (
    collectionName: string,
    options: {
      readonly vector: ReadonlyArray<number>;
      readonly limit: number;
      readonly with_payload: boolean;
    },
  ) => Effect.Effect<ReadonlyArray<QdrantScoredPoint>, QdrantClientError>;
}

export type QdrantClientFactory = (params: QdrantClientParams) => QdrantClientLike;

export const makeQdrantClient = (
  factory: QdrantClientFactory | undefined,
  params: QdrantClientParams,
): QdrantClientLike => {
  if (factory !== undefined) {
    return factory(params);
  }

  const client = new QdrantClient(params);
  const tryQdrantPromise = <A>(operation: string, try_: () => PromiseLike<A>) =>
    Effect.tryPromise({
      try: try_,
      catch: (cause) => qdrantClientError(operation, cause),
    });

  return {
    collectionExists: (collectionName) =>
      tryQdrantPromise("collection-exists", () => client.collectionExists(collectionName)),
    createCollection: (collectionName, options) =>
      tryQdrantPromise("create-collection", () => client.createCollection(collectionName, options)).pipe(
        Effect.asVoid,
      ),
    upsert: (collectionName, options) =>
      tryQdrantPromise("upsert", () =>
        client.upsert(collectionName, {
          points: options.points.map((point) => ({
            id: point.id,
            vector: Array.from(point.vector),
            ...(point.payload !== undefined ? { payload: point.payload } : {}),
          })),
        })
      ).pipe(Effect.asVoid),
    getCollections: tryQdrantPromise("get-collections", () => client.getCollections()),
    deleteCollection: (collectionName) =>
      tryQdrantPromise("delete-collection", () => client.deleteCollection(collectionName)).pipe(
        Effect.asVoid,
      ),
    search: (collectionName, options) =>
      tryQdrantPromise("search", () =>
        client.search(collectionName, {
          vector: Array.from(options.vector),
          limit: options.limit,
          with_payload: options.with_payload,
        })
      ),
  };
};
