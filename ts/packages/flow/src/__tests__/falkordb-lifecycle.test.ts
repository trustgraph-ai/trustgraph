import { Effect } from "effect";
import { describe, expect, it } from "vitest";
import {
  FalkorDBTriplesQueryLive,
  FalkorDBTriplesQueryService,
  type FalkorDBClosableClient as FalkorDBQueryClient,
  type FalkorDBQueryGraph,
} from "../query/triples/falkordb.js";
import {
  FalkorDBTriplesStoreLive,
  FalkorDBTriplesStoreService,
  type FalkorDBClosableClient as FalkorDBStoreClient,
  type FalkorDBStoreGraph,
} from "../storage/triples/falkordb.js";

class FakeFalkorDBClient implements FalkorDBStoreClient, FalkorDBQueryClient {
  connectCount = 0;
  disconnectCount = 0;

  readonly connect: Effect.Effect<void> = Effect.sync(() => {
    this.connectCount += 1;
  });

  readonly disconnect: Effect.Effect<void> = Effect.sync(() => {
    this.disconnectCount += 1;
  });
}

class FakeStoreGraph implements FalkorDBStoreGraph {
  readonly queries: string[] = [];

  query<T = unknown>(query: string): Effect.Effect<{ readonly data?: Array<T> }> {
    return Effect.sync(() => {
      this.queries.push(query);
      return {};
    });
  }
}

class FakeQueryGraph implements FalkorDBQueryGraph {
  readonly queries: string[] = [];

  query<T = unknown>(query: string): Effect.Effect<{ readonly data?: Array<T> }> {
    return Effect.sync(() => {
      this.queries.push(query);
      return {};
    });
  }
}

describe("FalkorDB scoped layers", () => {
  it("connects and disconnects the triples store client with the layer scope", async () => {
    const client = new FakeFalkorDBClient();
    const graph = new FakeStoreGraph();

    await Effect.runPromise(
      Effect.scoped(
        Effect.gen(function* () {
          const store = yield* FalkorDBTriplesStoreService;
          yield* store.deleteCollection("alice", "demo");
        }).pipe(
          Effect.provide(
            FalkorDBTriplesStoreLive({
              url: "redis://falkor.test:6379",
              database: "test-store",
              clientFactory: () => client,
              graphFactory: () => graph,
            }),
          ),
        ),
      ),
    );

    expect(client.connectCount).toBe(1);
    expect(client.disconnectCount).toBe(1);
    expect(graph.queries).toHaveLength(3);
  });

  it("connects and disconnects the triples query client with the layer scope", async () => {
    const client = new FakeFalkorDBClient();
    const graph = new FakeQueryGraph();

    const triples = await Effect.runPromise(
      Effect.scoped(
        Effect.gen(function* () {
          const query = yield* FalkorDBTriplesQueryService;
          return yield* query.queryTriples(undefined, undefined, undefined, 10);
        }).pipe(
          Effect.provide(
            FalkorDBTriplesQueryLive({
              url: "redis://falkor.test:6379",
              database: "test-query",
              clientFactory: () => client,
              graphFactory: () => graph,
            }),
          ),
        ),
      ),
    );

    expect(triples).toEqual([]);
    expect(client.connectCount).toBe(1);
    expect(client.disconnectCount).toBe(1);
    expect(graph.queries).toHaveLength(2);
  });
});
