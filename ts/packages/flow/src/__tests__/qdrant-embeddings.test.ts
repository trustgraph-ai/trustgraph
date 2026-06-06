import { Effect } from "effect";
import { describe, expect, it } from "vitest";
import {
  QdrantDocEmbeddingsQueryLive,
  QdrantDocEmbeddingsQueryService,
} from "../query/embeddings/qdrant-doc.js";
import {
  QdrantGraphEmbeddingsQueryLive,
  QdrantGraphEmbeddingsQueryService,
} from "../query/embeddings/qdrant-graph.js";
import type { QdrantClientLike, QdrantScoredPoint } from "../qdrant/client.js";
import { makeQdrantDocEmbeddingsStore } from "../storage/embeddings/qdrant-doc.js";
import {
  QdrantGraphEmbeddingsStoreLive,
  QdrantGraphEmbeddingsStoreService,
} from "../storage/embeddings/qdrant-graph.js";
import type { Term } from "@trustgraph/base";

interface FakePoint {
  readonly id: string;
  readonly vector: ReadonlyArray<number>;
  readonly payload?: Record<string, unknown>;
}

class FakeQdrantClient implements QdrantClientLike {
  readonly collections = new Set<string>();
  readonly collectionExistsCalls: string[] = [];
  readonly createdCollections: Array<{ readonly name: string; readonly size: number }> = [];
  readonly upserts: Array<{
    readonly collectionName: string;
    readonly points: ReadonlyArray<FakePoint>;
  }> = [];
  readonly deletedCollections: string[] = [];
  searchResults: ReadonlyArray<QdrantScoredPoint> = [];

  collectionExists(collectionName: string): Effect.Effect<{ readonly exists: boolean }> {
    return Effect.sync(() => {
      this.collectionExistsCalls.push(collectionName);
      return { exists: this.collections.has(collectionName) };
    });
  }

  createCollection(
    collectionName: string,
    options: { readonly vectors: { readonly size: number; readonly distance: "Cosine" } },
  ): Effect.Effect<void> {
    return Effect.sync(() => {
      this.collections.add(collectionName);
      this.createdCollections.push({ name: collectionName, size: options.vectors.size });
    });
  }

  upsert(
    collectionName: string,
    options: { readonly points: ReadonlyArray<FakePoint> },
  ): Effect.Effect<void> {
    return Effect.sync(() => {
      this.upserts.push({ collectionName, points: options.points });
    });
  }

  readonly getCollections: Effect.Effect<{ readonly collections: ReadonlyArray<{ readonly name: string }> }> =
    Effect.sync(() => ({ collections: Array.from(this.collections, (name) => ({ name })) }));

  deleteCollection(collectionName: string): Effect.Effect<void> {
    return Effect.sync(() => {
      this.collections.delete(collectionName);
      this.deletedCollections.push(collectionName);
    });
  }

  search(
    _collectionName: string,
    _options: {
      readonly vector: ReadonlyArray<number>;
      readonly limit: number;
      readonly with_payload: boolean;
    },
  ): Effect.Effect<ReadonlyArray<QdrantScoredPoint>> {
    return Effect.sync(() => this.searchResults);
  }
}

describe("Qdrant embeddings", () => {
  it("queries graph payloads through Schema and skips malformed points", async () => {
    const client = new FakeQdrantClient();
    client.collections.add("t_alice_demo_2");
    client.searchResults = [
      { score: 0.9, payload: { entity: "https://example.com/entity" } },
      { score: 0.8, payload: { entity: 123 } },
      { score: 0.7, payload: { entity: "" } },
      { score: 0.6, payload: { entity: "plain entity" } },
    ];

    const matches = await Effect.runPromise(
      Effect.gen(function* () {
        const query = yield* QdrantGraphEmbeddingsQueryService;
        return yield* query.query({
          vector: [0.1, 0.2],
          user: "alice",
          collection: "demo",
          limit: 10,
        });
      }).pipe(
        Effect.provide(
          QdrantGraphEmbeddingsQueryLive({
            url: "http://qdrant.test",
            clientFactory: () => client,
          }),
        ),
      ),
    );

    expect(matches).toEqual([
      {
        entity: { type: "IRI", iri: "https://example.com/entity" },
        score: 0.9,
      },
      {
        entity: { type: "LITERAL", value: "plain entity" },
        score: 0.6,
      },
    ]);
  });

  it("queries document payloads through Schema and skips malformed points", async () => {
    const client = new FakeQdrantClient();
    client.collections.add("d_alice_docs_2");
    client.searchResults = [
      { score: 0.9, payload: { chunk_id: "chunk-a", content: "alpha" } },
      { score: 0.8, payload: { chunk_id: 123, content: "bad" } },
      { score: 0.7, payload: { chunk_id: "" } },
      { score: 0.6, payload: { chunk_id: "chunk-b" } },
    ];

    const matches = await Effect.runPromise(
      Effect.gen(function* () {
        const query = yield* QdrantDocEmbeddingsQueryService;
        return yield* query.query({
          vector: [0.1, 0.2],
          user: "alice",
          collection: "docs",
          limit: 10,
        });
      }).pipe(
        Effect.provide(
          QdrantDocEmbeddingsQueryLive({
            url: "http://qdrant.test",
            clientFactory: () => client,
          }),
        ),
      ),
    );

    expect(matches).toEqual([
      { chunkId: "chunk-a", score: 0.9, content: "alpha" },
      { chunkId: "chunk-b", score: 0.6 },
    ]);
  });

  it("uses an injected graph store client for collection creation and upsert", async () => {
    const client = new FakeQdrantClient();
    const entity: Term = { type: "IRI", iri: "https://example.com/entity" };

    await Effect.runPromise(
      Effect.gen(function* () {
        const store = yield* QdrantGraphEmbeddingsStoreService;
        yield* store.store({
          user: "alice",
          collection: "graph",
          entities: [{ entity, vector: [1, 2, 3], chunkId: "chunk-a" }],
        });
        yield* store.store({
          user: "alice",
          collection: "graph",
          entities: [{ entity, vector: [3, 2, 1], chunkId: "chunk-b" }],
        });
        yield* store.deleteCollection("alice", "graph");
        yield* store.store({
          user: "alice",
          collection: "graph",
          entities: [{ entity, vector: [1, 1, 1], chunkId: "chunk-c" }],
        });
      }).pipe(
        Effect.provide(
          QdrantGraphEmbeddingsStoreLive({
            url: "http://qdrant.test",
            clientFactory: () => client,
          }),
        ),
      ),
    );

    expect(client.collectionExistsCalls).toEqual(["t_alice_graph_3", "t_alice_graph_3"]);
    expect(client.createdCollections).toEqual([
      { name: "t_alice_graph_3", size: 3 },
      { name: "t_alice_graph_3", size: 3 },
    ]);
    expect(client.deletedCollections).toEqual(["t_alice_graph_3"]);
    expect(client.upserts).toHaveLength(3);
    expect(client.upserts[0]?.collectionName).toBe("t_alice_graph_3");
    expect(client.upserts[0]?.points[0]?.payload).toEqual({
      entity: "https://example.com/entity",
      chunk_id: "chunk-a",
    });
  });

  it("uses an injected document store client for collection creation and upsert", async () => {
    const client = new FakeQdrantClient();
    const store = makeQdrantDocEmbeddingsStore({
      url: "http://qdrant.test",
      clientFactory: () => client,
    });

    await Effect.runPromise(
      store.store({
        user: "alice",
        collection: "docs",
        chunks: [{ chunkId: "chunk-a", vector: [1, 2], content: "alpha" }],
      }),
    );
    await Effect.runPromise(
      store.store({
        user: "alice",
        collection: "docs",
        chunks: [{ chunkId: "chunk-b", vector: [2, 1], content: "beta" }],
      }),
    );
    await Effect.runPromise(store.deleteCollection("alice", "docs"));
    await Effect.runPromise(
      store.store({
        user: "alice",
        collection: "docs",
        chunks: [{ chunkId: "chunk-c", vector: [1, 1], content: "gamma" }],
      }),
    );

    expect(client.collectionExistsCalls).toEqual([
      "d_alice_docs_2",
      "d_alice_docs_2",
      "d_alice_docs_2",
    ]);
    expect(client.createdCollections).toEqual([
      { name: "d_alice_docs_2", size: 2 },
      { name: "d_alice_docs_2", size: 2 },
    ]);
    expect(client.deletedCollections).toEqual(["d_alice_docs_2"]);
    expect(client.upserts).toHaveLength(3);
    expect(client.upserts[0]?.collectionName).toBe("d_alice_docs_2");
    expect(client.upserts[0]?.points[0]?.payload).toEqual({
      chunk_id: "chunk-a",
      content: "alpha",
    });
  });
});
