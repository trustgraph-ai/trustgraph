/**
 * Qdrant graph embeddings write service.
 *
 * Stores entity/vector pairs in Qdrant for graph embeddings lookup.
 * Collection naming: t_{user}_{collection}_{dimension}
 * Collections are lazily created on first write with cosine distance.
 *
 * Python reference: trustgraph-flow/trustgraph/storage/graph_embeddings/qdrant/write.py
 */

import type { Term } from "@trustgraph/base";
import { errorMessage, } from "@trustgraph/base";
import { Config, Context, Effect, Layer, Match, Random } from "effect";
import * as MutableHashSet from "effect/MutableHashSet";
import * as O from "effect/Option";
import * as S from "effect/Schema";
import type { QdrantClientFactory, QdrantClientLike } from "../../qdrant/client.js";
import { makeQdrantClient, } from "../../qdrant/client.js";

export interface QdrantGraphEmbeddingsConfig {
  url?: string;
  apiKey?: string;
  clientFactory?: QdrantClientFactory;
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
    cause: S.Defect({ includeStack: true }),
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
  return Match.type<Term>().pipe(
    Match.discriminatorsExhaustive("type")({
      IRI: (iri) => iri.iri,
      LITERAL: (literal) => literal.value,
      BLANK: (blank) => blank.id,
      TRIPLE: () => null,
    }),
  )(term);
}

export interface QdrantGraphEmbeddingsStore {
  readonly store: (
    message: GraphEmbeddingsMessage,
  ) => Effect.Effect<void, QdrantGraphEmbeddingsStoreError>;
  readonly deleteCollection: (
    user: string,
    collection: string,
  ) => Effect.Effect<void, QdrantGraphEmbeddingsStoreError>;
}

const makeQdrantGraphEmbeddingsClient = (
  config: QdrantGraphEmbeddingsConfig,
  resolved: ResolvedQdrantGraphEmbeddingsConfig,
) =>
  Effect.try({
    try: () =>
      makeQdrantClient(config.clientFactory, {
        url: resolved.url,
        ...(resolved.apiKey !== undefined ? { apiKey: resolved.apiKey } : {}),
      }),
    catch: (cause) => qdrantGraphEmbeddingsStoreError("create-client", cause),
  });

const makeQdrantGraphEmbeddingsStoreFromClient = (
  client: QdrantClientLike,
): QdrantGraphEmbeddingsStoreServiceShape => {
  const knownCollections = MutableHashSet.empty<string>();

  const collectionName = (user: string, collection: string, dim: number): string =>
    `t_${user}_${collection}_${dim}`;

  const ensureCollectionEffect = Effect.fn("QdrantGraphEmbeddings.ensureCollection")(function* (
    name: string,
    dim: number,
  ) {
    if (MutableHashSet.has(knownCollections, name)) return;

    const exists = yield* client.collectionExists(name).pipe(
      Effect.mapError((cause) => qdrantGraphEmbeddingsStoreError("collection-exists", cause)),
    );
    if (!exists.exists) {
      yield* Effect.log(`[QdrantGraphEmbeddings] Creating collection ${name} (dim=${dim})`);
      yield* client.createCollection(
        name,
        {
          vectors: { size: dim, distance: "Cosine" },
        },
      ).pipe(
        Effect.mapError((cause) => qdrantGraphEmbeddingsStoreError("create-collection", cause)),
      );
    }

    MutableHashSet.add(knownCollections, name);
  });

  const storeImpl = Effect.fn("QdrantGraphEmbeddings.store")(function* (message: GraphEmbeddingsMessage) {
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
      yield* client.upsert(
        name,
        {
          points: [
            {
              id,
              vector: entry.vector,
              payload,
            },
          ],
        },
      ).pipe(
        Effect.mapError((cause) => qdrantGraphEmbeddingsStoreError("upsert", cause)),
      );
    }
  });

  const deleteCollectionImpl = Effect.fn("QdrantGraphEmbeddings.deleteCollection")(function* (
    user: string,
    collection: string,
  ) {
    const prefix = `t_${user}_${collection}_`;

    const allCollections = yield* client.getCollections.pipe(
      Effect.mapError((cause) => qdrantGraphEmbeddingsStoreError("get-collections", cause)),
    );
    const matching = allCollections.collections.filter((c) =>
      c.name.startsWith(prefix),
    );

    if (matching.length === 0) {
      yield* Effect.log(`[QdrantGraphEmbeddings] No collections matching prefix ${prefix}`);
      return;
    }

    for (const coll of matching) {
      yield* client.deleteCollection(coll.name).pipe(
        Effect.mapError((cause) => qdrantGraphEmbeddingsStoreError("delete-collection", cause)),
      );
      MutableHashSet.remove(knownCollections, coll.name);
      yield* Effect.log(`[QdrantGraphEmbeddings] Deleted collection: ${coll.name}`);
    }

    yield* Effect.log(
      `[QdrantGraphEmbeddings] Deleted ${matching.length} collection(s) for ${user}/${collection}`,
    );
  });

  return {
    store: storeImpl,
    deleteCollection: deleteCollectionImpl,
  };
};

export const makeQdrantGraphEmbeddingsStoreServiceEffect = Effect.fn(
  "makeQdrantGraphEmbeddingsStoreServiceEffect",
)(function* (config: QdrantGraphEmbeddingsConfig = {}) {
  const resolved = yield* loadQdrantGraphEmbeddingsConfig(config).pipe(
    Effect.mapError((cause) => qdrantGraphEmbeddingsStoreError("load-config", cause)),
  );
  const client = yield* makeQdrantGraphEmbeddingsClient(config, resolved);
  yield* Effect.log("[QdrantGraphEmbeddings] Store initialized");
  return makeQdrantGraphEmbeddingsStoreFromClient(client);
});

const withQdrantGraphEmbeddingsStore = <A>(
  config: QdrantGraphEmbeddingsConfig,
  use: (store: QdrantGraphEmbeddingsStoreServiceShape) => Effect.Effect<A, QdrantGraphEmbeddingsStoreError>,
) =>
  makeQdrantGraphEmbeddingsStoreServiceEffect(config).pipe(
    Effect.flatMap(use),
  );

export function makeQdrantGraphEmbeddingsStore(
  config: QdrantGraphEmbeddingsConfig = {},
): QdrantGraphEmbeddingsStore {
  return {
    store: (message) => withQdrantGraphEmbeddingsStore(config, (store) => store.store(message)),
    deleteCollection: (user, collection) =>
      withQdrantGraphEmbeddingsStore(config, (store) => store.deleteCollection(user, collection)),
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
): QdrantGraphEmbeddingsStoreServiceShape => ({
  store: (message) => withQdrantGraphEmbeddingsStore(config, (store) => store.store(message)),
  deleteCollection: (user, collection) =>
    withQdrantGraphEmbeddingsStore(config, (store) => store.deleteCollection(user, collection)),
});

export const QdrantGraphEmbeddingsStoreLive = (
  config: QdrantGraphEmbeddingsConfig = {},
): Layer.Layer<QdrantGraphEmbeddingsStoreService, QdrantGraphEmbeddingsStoreError> =>
  Layer.effect(
    QdrantGraphEmbeddingsStoreService,
    makeQdrantGraphEmbeddingsStoreServiceEffect(config).pipe(
      Effect.map((service) => QdrantGraphEmbeddingsStoreService.of(service)),
    ),
  );
