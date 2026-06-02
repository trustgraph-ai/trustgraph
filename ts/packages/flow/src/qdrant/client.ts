import { QdrantClient, type QdrantClientParams } from "@qdrant/js-client-rest";

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

export interface QdrantClientLike {
  readonly collectionExists: (collectionName: string) => Promise<QdrantCollectionStatus>;
  readonly createCollection: (
    collectionName: string,
    options: {
      readonly vectors: {
        readonly size: number;
        readonly distance: "Cosine";
      };
    },
  ) => Promise<unknown>;
  readonly upsert: (
    collectionName: string,
    options: {
      readonly points: ReadonlyArray<{
        readonly id: string;
        readonly vector: ReadonlyArray<number>;
        readonly payload?: Record<string, unknown>;
      }>;
    },
  ) => Promise<unknown>;
  readonly getCollections: () => Promise<QdrantCollections>;
  readonly deleteCollection: (collectionName: string) => Promise<unknown>;
  readonly search: (
    collectionName: string,
    options: {
      readonly vector: ReadonlyArray<number>;
      readonly limit: number;
      readonly with_payload: boolean;
    },
  ) => Promise<ReadonlyArray<QdrantScoredPoint>>;
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
  return {
    collectionExists: (collectionName) => client.collectionExists(collectionName),
    createCollection: (collectionName, options) => client.createCollection(collectionName, options),
    upsert: (collectionName, options) =>
      client.upsert(collectionName, {
        points: options.points.map((point) => ({
          id: point.id,
          vector: Array.from(point.vector),
          ...(point.payload !== undefined ? { payload: point.payload } : {}),
        })),
      }),
    getCollections: () => client.getCollections(),
    deleteCollection: (collectionName) => client.deleteCollection(collectionName),
    search: (collectionName, options) =>
      client.search(collectionName, {
        vector: Array.from(options.vector),
        limit: options.limit,
        with_payload: options.with_payload,
      }),
  };
};
