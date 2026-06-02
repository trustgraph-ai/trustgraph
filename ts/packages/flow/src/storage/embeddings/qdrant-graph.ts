/**
 * Qdrant graph embeddings write service.
 *
 * Stores entity/vector pairs in Qdrant for graph embeddings lookup.
 * Collection naming: t_{user}_{collection}_{dimension}
 * Collections are lazily created on first write with cosine distance.
 *
 * Python reference: trustgraph-flow/trustgraph/storage/graph_embeddings/qdrant/write.py
 */

import { QdrantClient } from "@qdrant/js-client-rest";
import { errorMessage, type Term } from "@trustgraph/base";
import { Context, Effect, Layer } from "effect";
import * as S from "effect/Schema";

export interface QdrantGraphEmbeddingsConfig {
  url?: string;
  apiKey?: string;
}

export interface GraphEmbeddingEntity {
  entity: Term;
  vector: number[];
  chunkId?: string;
}

export interface GraphEmbeddingsMessage {
  user: string;
  collection: string;
  entities: GraphEmbeddingEntity[];
}

function getTermValue(term: Term): string | null {
  switch (term.type) {
    case "IRI":
      return term.iri;
    case "LITERAL":
      return term.value;
    case "BLANK":
      return term.id;
    case "TRIPLE":
      return null;
  }
}

export interface QdrantGraphEmbeddingsStore {
  readonly store: (message: GraphEmbeddingsMessage) => Promise<void>;
  readonly deleteCollection: (user: string, collection: string) => Promise<void>;
}

export function makeQdrantGraphEmbeddingsStore(
  config: QdrantGraphEmbeddingsConfig = {},
): QdrantGraphEmbeddingsStore {
  const url = config.url ?? process.env.QDRANT_URL ?? "http://localhost:6333";
  const apiKey = config.apiKey ?? process.env.QDRANT_API_KEY;

  const client = new QdrantClient({
    url,
    ...(apiKey !== undefined && apiKey.length > 0 ? { apiKey } : {}),
  });
  const knownCollections = new Set<string>();

  console.log("[QdrantGraphEmbeddings] Store initialized");

  const collectionName = (user: string, collection: string, dim: number): string =>
    `t_${user}_${collection}_${dim}`;

  const ensureCollection = async (name: string, dim: number): Promise<void> => {
    if (knownCollections.has(name)) return;

    const exists = await client.collectionExists(name);
    if (!exists.exists) {
      console.log(`[QdrantGraphEmbeddings] Creating collection ${name} (dim=${dim})`);
      await client.createCollection(name, {
        vectors: { size: dim, distance: "Cosine" },
      });
    }

    knownCollections.add(name);
  };

  const store = async (message: GraphEmbeddingsMessage): Promise<void> => {
    for (const entry of message.entities) {
      const entityValue = getTermValue(entry.entity);
      if (entityValue === null || entityValue.length === 0) continue;
      if (entry.vector.length === 0) continue;

      const dim = entry.vector.length;
      const name = collectionName(message.user, message.collection, dim);

      await ensureCollection(name, dim);

      const payload: Record<string, unknown> = { entity: entityValue };
      if (entry.chunkId !== undefined && entry.chunkId.length > 0) {
        payload.chunk_id = entry.chunkId;
      }

      await client.upsert(name, {
        points: [
          {
            id: crypto.randomUUID(),
            vector: entry.vector,
            payload,
          },
        ],
      });
    }
  };

  const deleteCollection = async (user: string, collection: string): Promise<void> => {
    const prefix = `t_${user}_${collection}_`;

    const allCollections = await client.getCollections();
    const matching = allCollections.collections.filter((c) =>
      c.name.startsWith(prefix),
    );

    if (matching.length === 0) {
      console.log(`[QdrantGraphEmbeddings] No collections matching prefix ${prefix}`);
      return;
    }

    for (const coll of matching) {
      await client.deleteCollection(coll.name);
      knownCollections.delete(coll.name);
      console.log(`[QdrantGraphEmbeddings] Deleted collection: ${coll.name}`);
    }

    console.log(
      `[QdrantGraphEmbeddings] Deleted ${matching.length} collection(s) for ${user}/${collection}`,
    );
  };

  return { store, deleteCollection };
}

export class QdrantGraphEmbeddingsStoreError extends S.TaggedErrorClass<QdrantGraphEmbeddingsStoreError>()(
  "QdrantGraphEmbeddingsStoreError",
  {
    message: S.String,
    operation: S.String,
    cause: S.DefectWithStack,
  },
) {}

export interface QdrantGraphEmbeddingsStoreServiceShape {
  readonly store: (
    message: GraphEmbeddingsMessage,
  ) => Effect.Effect<void, QdrantGraphEmbeddingsStoreError>;
  readonly deleteCollection: (
    user: string,
    collection: string,
  ) => Effect.Effect<void, QdrantGraphEmbeddingsStoreError>;
}

export class QdrantGraphEmbeddingsStoreService extends Context.Service<
  QdrantGraphEmbeddingsStoreService,
  QdrantGraphEmbeddingsStoreServiceShape
>()(
  "@trustgraph/flow/storage/embeddings/qdrant-graph/QdrantGraphEmbeddingsStoreService",
) {}

const qdrantGraphEmbeddingsStoreError = (operation: string, cause: unknown) =>
  new QdrantGraphEmbeddingsStoreError({
    operation,
    message: errorMessage(cause),
    cause,
  });

export const makeQdrantGraphEmbeddingsStoreService = (
  config: QdrantGraphEmbeddingsConfig = {},
): QdrantGraphEmbeddingsStoreServiceShape => {
  const store = makeQdrantGraphEmbeddingsStore(config);
  return {
    store: Effect.fn("QdrantGraphEmbeddingsStore.store")(function* (message) {
      return yield* Effect.tryPromise({
        try: () => store.store(message),
        catch: (cause) => qdrantGraphEmbeddingsStoreError("store", cause),
      });
    }),
    deleteCollection: Effect.fn("QdrantGraphEmbeddingsStore.deleteCollection")(function* (
      user,
      collection,
    ) {
      return yield* Effect.tryPromise({
        try: () => store.deleteCollection(user, collection),
        catch: (cause) => qdrantGraphEmbeddingsStoreError("delete-collection", cause),
      });
    }),
  };
};

export const QdrantGraphEmbeddingsStoreLive = (
  config: QdrantGraphEmbeddingsConfig = {},
): Layer.Layer<QdrantGraphEmbeddingsStoreService> =>
  Layer.succeed(
    QdrantGraphEmbeddingsStoreService,
    QdrantGraphEmbeddingsStoreService.of(makeQdrantGraphEmbeddingsStoreService(config)),
  );
