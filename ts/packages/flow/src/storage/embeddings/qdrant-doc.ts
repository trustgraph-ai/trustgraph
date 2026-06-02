/**
 * Qdrant document embeddings write service.
 *
 * Stores document chunk embeddings in Qdrant for later similarity search.
 * Collection naming: d_{user}_{collection}_{dimension}
 * Collections are lazily created on first write with cosine distance.
 *
 * Python reference: trustgraph-flow/trustgraph/storage/doc_embeddings/qdrant/write.py
 */

import { errorMessage } from "@trustgraph/base";
import { Config, Effect, Random } from "effect";
import * as O from "effect/Option";
import * as S from "effect/Schema";
import { makeQdrantClient, type QdrantClientFactory, type QdrantClientLike } from "../../qdrant/client.js";

export interface QdrantDocEmbeddingsConfig {
  url?: string;
  apiKey?: string;
  clientFactory?: QdrantClientFactory;
}

export interface DocEmbeddingChunk {
  chunkId: string;
  vector: number[];
  content?: string;
}

export interface DocEmbeddingsMessage {
  user: string;
  collection: string;
  chunks: DocEmbeddingChunk[];
}

export class QdrantDocEmbeddingsStoreError extends S.TaggedErrorClass<QdrantDocEmbeddingsStoreError>()(
  "QdrantDocEmbeddingsStoreError",
  {
    message: S.String,
    operation: S.String,
    cause: S.DefectWithStack,
  },
) {}

const qdrantDocEmbeddingsStoreError = (operation: string, cause: unknown) =>
  QdrantDocEmbeddingsStoreError.make({
    operation,
    message: errorMessage(cause),
    cause,
  });

interface ResolvedQdrantDocEmbeddingsConfig {
  readonly url: string;
  readonly apiKey?: string;
}

const loadQdrantDocEmbeddingsConfig = Effect.fn("QdrantDocEmbeddings.loadConfig")(function* (
  config: QdrantDocEmbeddingsConfig,
) {
  const envApiKey = O.getOrUndefined(yield* Config.string("QDRANT_API_KEY").pipe(Config.option));
  const apiKey = config.apiKey ?? envApiKey;
  return {
    url: config.url ?? (yield* Config.string("QDRANT_URL").pipe(Config.withDefault("http://localhost:6333"))),
    ...(apiKey !== undefined && apiKey.length > 0 ? { apiKey } : {}),
  } satisfies ResolvedQdrantDocEmbeddingsConfig;
});

const randomHex = Effect.fn("QdrantDocEmbeddings.randomHex")(function* (digits: number) {
  let result = "";
  for (let index = 0; index < digits; index++) {
    const value = yield* Random.nextIntBetween(0, 16);
    result += value.toString(16);
  }
  return result;
});

const randomPointId = Effect.fn("QdrantDocEmbeddings.randomPointId")(function* () {
  const part1 = yield* randomHex(8);
  const part2 = yield* randomHex(4);
  const versionRest = yield* randomHex(3);
  const variant = yield* Random.nextIntBetween(8, 12);
  const variantRest = yield* randomHex(3);
  const part5 = yield* randomHex(12);
  return `${part1}-${part2}-4${versionRest}-${variant.toString(16)}${variantRest}-${part5}`;
});

export interface QdrantDocEmbeddingsStore {
  readonly store: (message: DocEmbeddingsMessage) => Promise<void>;
  readonly deleteCollection: (user: string, collection: string) => Promise<void>;
  readonly storeEffect: (
    message: DocEmbeddingsMessage,
  ) => Effect.Effect<void, QdrantDocEmbeddingsStoreError>;
  readonly deleteCollectionEffect: (
    user: string,
    collection: string,
  ) => Effect.Effect<void, QdrantDocEmbeddingsStoreError>;
}

const makeQdrantDocEmbeddingsClient = (
  config: QdrantDocEmbeddingsConfig,
  resolved: ResolvedQdrantDocEmbeddingsConfig,
) =>
  Effect.try({
    try: () =>
      makeQdrantClient(config.clientFactory, {
        url: resolved.url,
        ...(resolved.apiKey !== undefined ? { apiKey: resolved.apiKey } : {}),
      }),
    catch: (cause) => qdrantDocEmbeddingsStoreError("create-client", cause),
  });

interface QdrantDocEmbeddingsStoreEffectShape {
  readonly store: (
    message: DocEmbeddingsMessage,
  ) => Effect.Effect<void, QdrantDocEmbeddingsStoreError>;
  readonly deleteCollection: (
    user: string,
    collection: string,
  ) => Effect.Effect<void, QdrantDocEmbeddingsStoreError>;
}

const makeQdrantDocEmbeddingsStoreFromClient = (
  client: QdrantClientLike,
): QdrantDocEmbeddingsStoreEffectShape => {
  const knownCollections = new Set<string>();

  const collectionName = (user: string, collection: string, dim: number): string =>
    `d_${user}_${collection}_${dim}`;

  const ensureCollectionEffect = Effect.fn("QdrantDocEmbeddings.ensureCollection")(function* (
    name: string,
    dim: number,
  ) {
    if (knownCollections.has(name)) return;

    const exists = yield* Effect.tryPromise({
      try: () => client.collectionExists(name),
      catch: (cause) => qdrantDocEmbeddingsStoreError("collection-exists", cause),
    });
    if (!exists.exists) {
      yield* Effect.log(`[QdrantDocEmbeddings] Creating collection ${name} (dim=${dim})`);
      yield* Effect.tryPromise({
        try: () =>
          client.createCollection(name, {
            vectors: { size: dim, distance: "Cosine" },
          }),
        catch: (cause) => qdrantDocEmbeddingsStoreError("create-collection", cause),
      });
    }

    knownCollections.add(name);
  });

  const storeEffect = Effect.fn("QdrantDocEmbeddings.store")(function* (message: DocEmbeddingsMessage) {
    for (const chunk of message.chunks) {
      if (chunk.chunkId.length === 0) continue;
      if (chunk.vector.length === 0) continue;

      const dim = chunk.vector.length;
      const name = collectionName(message.user, message.collection, dim);

      yield* ensureCollectionEffect(name, dim);

      const id = yield* randomPointId();
      yield* Effect.tryPromise({
        try: () =>
          client.upsert(name, {
            points: [
              {
                id,
                vector: chunk.vector,
                payload: {
                  chunk_id: chunk.chunkId,
                  ...(chunk.content !== undefined && chunk.content.length > 0
                    ? { content: chunk.content }
                    : {}),
                },
              },
            ],
          }),
        catch: (cause) => qdrantDocEmbeddingsStoreError("upsert", cause),
      });
    }
  });

  const deleteCollectionEffect = Effect.fn("QdrantDocEmbeddings.deleteCollection")(function* (
    user: string,
    collection: string,
  ) {
    const prefix = `d_${user}_${collection}_`;

    const allCollections = yield* Effect.tryPromise({
      try: () => client.getCollections(),
      catch: (cause) => qdrantDocEmbeddingsStoreError("get-collections", cause),
    });
    const matching = allCollections.collections.filter((c) =>
      c.name.startsWith(prefix),
    );

    if (matching.length === 0) {
      yield* Effect.log(`[QdrantDocEmbeddings] No collections matching prefix ${prefix}`);
      return;
    }

    for (const coll of matching) {
      yield* Effect.tryPromise({
        try: () => client.deleteCollection(coll.name),
        catch: (cause) => qdrantDocEmbeddingsStoreError("delete-collection", cause),
      });
      knownCollections.delete(coll.name);
      yield* Effect.log(`[QdrantDocEmbeddings] Deleted collection: ${coll.name}`);
    }

    yield* Effect.log(
      `[QdrantDocEmbeddings] Deleted ${matching.length} collection(s) for ${user}/${collection}`,
    );
  });

  return {
    store: storeEffect,
    deleteCollection: deleteCollectionEffect,
  };
};

const makeQdrantDocEmbeddingsStoreEffect = Effect.fn("makeQdrantDocEmbeddingsStoreEffect")(function* (
  config: QdrantDocEmbeddingsConfig = {},
) {
  const resolved = yield* loadQdrantDocEmbeddingsConfig(config).pipe(
    Effect.mapError((cause) => qdrantDocEmbeddingsStoreError("load-config", cause)),
  );
  const client = yield* makeQdrantDocEmbeddingsClient(config, resolved);
  yield* Effect.log("[QdrantDocEmbeddings] Store initialized");
  return makeQdrantDocEmbeddingsStoreFromClient(client);
});

const withQdrantDocEmbeddingsStore = <A>(
  config: QdrantDocEmbeddingsConfig,
  use: (store: QdrantDocEmbeddingsStoreEffectShape) => Effect.Effect<A, QdrantDocEmbeddingsStoreError>,
) =>
  makeQdrantDocEmbeddingsStoreEffect(config).pipe(
    Effect.flatMap(use),
  );

export function makeQdrantDocEmbeddingsStore(
  config: QdrantDocEmbeddingsConfig = {},
): QdrantDocEmbeddingsStore {
  const storeEffect = (message: DocEmbeddingsMessage) =>
    withQdrantDocEmbeddingsStore(config, (store) => store.store(message));
  const deleteCollectionEffect = (user: string, collection: string) =>
    withQdrantDocEmbeddingsStore(config, (store) => store.deleteCollection(user, collection));

  return {
    store: (message) => Effect.runPromise(storeEffect(message)),
    deleteCollection: (user, collection) =>
      Effect.runPromise(deleteCollectionEffect(user, collection)),
    storeEffect,
    deleteCollectionEffect,
  };
}
