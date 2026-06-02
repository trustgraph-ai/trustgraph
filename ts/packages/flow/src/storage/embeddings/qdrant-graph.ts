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
import { Config, Context, Effect, Layer, Random } from "effect";
import * as O from "effect/Option";
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

export class QdrantGraphEmbeddingsStoreError extends S.TaggedErrorClass<QdrantGraphEmbeddingsStoreError>()(
  "QdrantGraphEmbeddingsStoreError",
  {
    message: S.String,
    operation: S.String,
    cause: S.DefectWithStack,
  },
) {}

const qdrantGraphEmbeddingsStoreError = (operation: string, cause: unknown) =>
  QdrantGraphEmbeddingsStoreError.make({
    operation,
    message: errorMessage(cause),
    cause,
  });

interface ResolvedQdrantGraphEmbeddingsConfig {
  readonly url: string;
  readonly apiKey?: string;
}

const loadQdrantGraphEmbeddingsConfig = Effect.fn("QdrantGraphEmbeddings.loadConfig")(function* (
  config: QdrantGraphEmbeddingsConfig,
) {
  const envApiKey = O.getOrUndefined(yield* Config.string("QDRANT_API_KEY").pipe(Config.option));
  const apiKey = config.apiKey ?? envApiKey;
  return {
    url: config.url ?? (yield* Config.string("QDRANT_URL").pipe(Config.withDefault("http://localhost:6333"))),
    ...(apiKey !== undefined && apiKey.length > 0 ? { apiKey } : {}),
  } satisfies ResolvedQdrantGraphEmbeddingsConfig;
});

const randomHex = Effect.fn("QdrantGraphEmbeddings.randomHex")(function* (digits: number) {
  let result = "";
  for (let index = 0; index < digits; index++) {
    const value = yield* Random.nextIntBetween(0, 16);
    result += value.toString(16);
  }
  return result;
});

const randomPointId = Effect.fn("QdrantGraphEmbeddings.randomPointId")(function* () {
  const part1 = yield* randomHex(8);
  const part2 = yield* randomHex(4);
  const versionRest = yield* randomHex(3);
  const variant = yield* Random.nextIntBetween(8, 12);
  const variantRest = yield* randomHex(3);
  const part5 = yield* randomHex(12);
  return `${part1}-${part2}-4${versionRest}-${variant.toString(16)}${variantRest}-${part5}`;
});

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
  readonly storeEffect: (
    message: GraphEmbeddingsMessage,
  ) => Effect.Effect<void, QdrantGraphEmbeddingsStoreError>;
  readonly deleteCollectionEffect: (
    user: string,
    collection: string,
  ) => Effect.Effect<void, QdrantGraphEmbeddingsStoreError>;
}

export function makeQdrantGraphEmbeddingsStore(
  config: QdrantGraphEmbeddingsConfig = {},
): QdrantGraphEmbeddingsStore {
  const resolved = Effect.runSync(loadQdrantGraphEmbeddingsConfig(config));

  const client = new QdrantClient({
    url: resolved.url,
    ...(resolved.apiKey !== undefined ? { apiKey: resolved.apiKey } : {}),
  });
  const knownCollections = new Set<string>();

  Effect.runSync(Effect.log("[QdrantGraphEmbeddings] Store initialized"));

  const collectionName = (user: string, collection: string, dim: number): string =>
    `t_${user}_${collection}_${dim}`;

  const ensureCollectionEffect = Effect.fn("QdrantGraphEmbeddings.ensureCollection")(function* (
    name: string,
    dim: number,
  ) {
    if (knownCollections.has(name)) return;

    const exists = yield* Effect.tryPromise({
      try: () => client.collectionExists(name),
      catch: (cause) => qdrantGraphEmbeddingsStoreError("collection-exists", cause),
    });
    if (!exists.exists) {
      yield* Effect.log(`[QdrantGraphEmbeddings] Creating collection ${name} (dim=${dim})`);
      yield* Effect.tryPromise({
        try: () =>
          client.createCollection(name, {
            vectors: { size: dim, distance: "Cosine" },
          }),
        catch: (cause) => qdrantGraphEmbeddingsStoreError("create-collection", cause),
      });
    }

    knownCollections.add(name);
  });

  const storeEffect = Effect.fn("QdrantGraphEmbeddings.store")(function* (message: GraphEmbeddingsMessage) {
    for (const entry of message.entities) {
      const entityValue = getTermValue(entry.entity);
      if (entityValue === null || entityValue.length === 0) continue;
      if (entry.vector.length === 0) continue;

      const dim = entry.vector.length;
      const name = collectionName(message.user, message.collection, dim);

      yield* ensureCollectionEffect(name, dim);

      const payload: Record<string, unknown> = { entity: entityValue };
      if (entry.chunkId !== undefined && entry.chunkId.length > 0) {
        payload.chunk_id = entry.chunkId;
      }

      const id = yield* randomPointId();
      yield* Effect.tryPromise({
        try: () =>
          client.upsert(name, {
            points: [
              {
                id,
                vector: entry.vector,
                payload,
              },
            ],
          }),
        catch: (cause) => qdrantGraphEmbeddingsStoreError("upsert", cause),
      });
    }
  });

  const deleteCollectionEffect = Effect.fn("QdrantGraphEmbeddings.deleteCollection")(function* (
    user: string,
    collection: string,
  ) {
    const prefix = `t_${user}_${collection}_`;

    const allCollections = yield* Effect.tryPromise({
      try: () => client.getCollections(),
      catch: (cause) => qdrantGraphEmbeddingsStoreError("get-collections", cause),
    });
    const matching = allCollections.collections.filter((c) =>
      c.name.startsWith(prefix),
    );

    if (matching.length === 0) {
      yield* Effect.log(`[QdrantGraphEmbeddings] No collections matching prefix ${prefix}`);
      return;
    }

    for (const coll of matching) {
      yield* Effect.tryPromise({
        try: () => client.deleteCollection(coll.name),
        catch: (cause) => qdrantGraphEmbeddingsStoreError("delete-collection", cause),
      });
      knownCollections.delete(coll.name);
      yield* Effect.log(`[QdrantGraphEmbeddings] Deleted collection: ${coll.name}`);
    }

    yield* Effect.log(
      `[QdrantGraphEmbeddings] Deleted ${matching.length} collection(s) for ${user}/${collection}`,
    );
  });

  return {
    store: (message) => Effect.runPromise(storeEffect(message)),
    deleteCollection: (user, collection) =>
      Effect.runPromise(deleteCollectionEffect(user, collection)),
    storeEffect,
    deleteCollectionEffect,
  };
}

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

export const makeQdrantGraphEmbeddingsStoreService = (
  config: QdrantGraphEmbeddingsConfig = {},
): QdrantGraphEmbeddingsStoreServiceShape => {
  const store = makeQdrantGraphEmbeddingsStore(config);
  return {
    store: store.storeEffect,
    deleteCollection: store.deleteCollectionEffect,
  };
};

export const QdrantGraphEmbeddingsStoreLive = (
  config: QdrantGraphEmbeddingsConfig = {},
): Layer.Layer<QdrantGraphEmbeddingsStoreService> =>
  Layer.succeed(
    QdrantGraphEmbeddingsStoreService,
    QdrantGraphEmbeddingsStoreService.of(makeQdrantGraphEmbeddingsStoreService(config)),
  );
