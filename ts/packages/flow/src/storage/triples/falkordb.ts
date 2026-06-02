/**
 * FalkorDB triples store - writes RDF triples to a FalkorDB graph.
 *
 * FalkorDB is Redis-based and uses Cypher queries, same as the Python impl.
 * Pairs well with Graphiti which also uses FalkorDB as its backend.
 *
 * Python reference: trustgraph-flow/trustgraph/storage/triples/falkordb/write.py
 */

import { createClient, Graph } from "falkordb";
import { errorMessage, type Term, type Triple } from "@trustgraph/base";
import { Config, Context, Effect, Layer } from "effect";
import * as S from "effect/Schema";

export interface FalkorDBConfig {
  url?: string;
  database?: string;
}

function getTermValue(term: Term): string {
  switch (term.type) {
    case "IRI":
      return term.iri;
    case "LITERAL":
      return term.value;
    case "BLANK":
      return term.id;
    case "TRIPLE":
      return getTermValue(term.triple.s);
  }
}

export interface FalkorDBTriplesStore {
  readonly createNode: (uri: string, user: string, collection: string) => Promise<void>;
  readonly createLiteral: (value: string, user: string, collection: string) => Promise<void>;
  readonly relateNode: (
    src: string,
    uri: string,
    dest: string,
    user: string,
    collection: string,
  ) => Promise<void>;
  readonly relateLiteral: (
    src: string,
    uri: string,
    dest: string,
    user: string,
    collection: string,
  ) => Promise<void>;
  readonly storeTriples: (
    triples: Triple[],
    user?: string,
    collection?: string,
  ) => Promise<void>;
  readonly deleteCollection: (user: string, collection: string) => Promise<void>;
}

export class FalkorDBTriplesStoreError extends S.TaggedErrorClass<FalkorDBTriplesStoreError>()(
  "FalkorDBTriplesStoreError",
  {
    message: S.String,
    operation: S.String,
    cause: S.DefectWithStack,
  },
) {}

export interface FalkorDBTriplesStoreServiceShape {
  readonly storeTriples: (
    triples: ReadonlyArray<Triple>,
    user: string,
    collection: string,
  ) => Effect.Effect<void, FalkorDBTriplesStoreError>;
  readonly deleteCollection: (
    user: string,
    collection: string,
  ) => Effect.Effect<void, FalkorDBTriplesStoreError>;
}

export class FalkorDBTriplesStoreService extends Context.Service<
  FalkorDBTriplesStoreService,
  FalkorDBTriplesStoreServiceShape
>()(
  "@trustgraph/flow/storage/triples/falkordb/FalkorDBTriplesStoreService",
) {}

const falkorDBTriplesStoreError = (operation: string, cause: unknown): FalkorDBTriplesStoreError =>
  FalkorDBTriplesStoreError.make({
    operation,
    message: errorMessage(cause),
    cause,
  });

interface FalkorDBStoreConnection {
  readonly graph: Graph;
}

type FalkorDBQueryOptions = Parameters<Graph["query"]>[1];

interface FalkorDBTriplesStoreEffectShape {
  readonly createNode: (
    uri: string,
    user: string,
    collection: string,
  ) => Effect.Effect<void, FalkorDBTriplesStoreError>;
  readonly createLiteral: (
    value: string,
    user: string,
    collection: string,
  ) => Effect.Effect<void, FalkorDBTriplesStoreError>;
  readonly relateNode: (
    src: string,
    uri: string,
    dest: string,
    user: string,
    collection: string,
  ) => Effect.Effect<void, FalkorDBTriplesStoreError>;
  readonly relateLiteral: (
    src: string,
    uri: string,
    dest: string,
    user: string,
    collection: string,
  ) => Effect.Effect<void, FalkorDBTriplesStoreError>;
  readonly storeTriples: (
    triples: ReadonlyArray<Triple>,
    user: string,
    collection: string,
  ) => Effect.Effect<void, FalkorDBTriplesStoreError>;
  readonly deleteCollection: (
    user: string,
    collection: string,
  ) => Effect.Effect<void, FalkorDBTriplesStoreError>;
}

const resolveFalkorDBStoreConfig = Effect.fn("FalkorDBTriplesStore.resolveConfig")(function* (
  config: FalkorDBConfig,
) {
  const url = config.url ?? (yield* Config.string("FALKORDB_URL").pipe(
    Config.withDefault("redis://localhost:6379"),
    Effect.mapError((cause) => falkorDBTriplesStoreError("config", cause)),
  ));
  return {
    url,
    database: config.database ?? "falkordb",
  };
});

const connectFalkorDBTriplesStore = (
  config: FalkorDBConfig,
): Effect.Effect<FalkorDBStoreConnection, FalkorDBTriplesStoreError> =>
  Effect.gen(function* () {
    const { url, database } = yield* resolveFalkorDBStoreConfig(config);
    const { client, graph } = yield* Effect.try({
      try: () => {
        const client = createClient({ url });
        return { client, graph: new Graph(client, database) };
      },
      catch: (cause) => falkorDBTriplesStoreError("create-client", cause),
    });

    yield* Effect.tryPromise({
      try: () => client.connect(),
      catch: (cause) => falkorDBTriplesStoreError("connect", cause),
    }).pipe(
      Effect.tapError((error) =>
        Effect.logError("[FalkorDBTriplesStore] Connection failed", {
          error: error.message,
          operation: error.operation,
        })
      ),
    );

    yield* Effect.log(`[FalkorDBTriplesStore] Connected to ${url}, graph: ${database}`);
    return { graph };
  });

const runGraphQuery = (
  graph: Graph,
  operation: string,
  query: string,
  options?: FalkorDBQueryOptions,
): Effect.Effect<void, FalkorDBTriplesStoreError> =>
  Effect.tryPromise({
    try: () => graph.query(query, options),
    catch: (cause) => falkorDBTriplesStoreError(operation, cause),
  }).pipe(
    Effect.asVoid,
  );

const makeFalkorDBTriplesStoreEffect = (
  config: FalkorDBConfig = {},
): FalkorDBTriplesStoreEffectShape => {
  let cachedConnection: Effect.Effect<FalkorDBStoreConnection, FalkorDBTriplesStoreError> | undefined;

  const getConnection = Effect.fn("FalkorDBTriplesStore.connection")(function* () {
    if (cachedConnection === undefined) {
      cachedConnection = yield* Effect.cached(connectFalkorDBTriplesStore(config));
    }
    return yield* cachedConnection;
  });

  const createNode = Effect.fn("FalkorDBTriplesStore.createNode")(function* (
    uri: string,
    user: string,
    collection: string,
  ) {
    const { graph } = yield* getConnection();
    yield* runGraphQuery(
      graph,
      "create-node",
      "MERGE (n:Node {uri: $uri, user: $user, collection: $collection})",
      { params: { uri, user, collection } },
    );
  });

  const createLiteral = Effect.fn("FalkorDBTriplesStore.createLiteral")(function* (
    value: string,
    user: string,
    collection: string,
  ) {
    const { graph } = yield* getConnection();
    yield* runGraphQuery(
      graph,
      "create-literal",
      "MERGE (n:Literal {value: $value, user: $user, collection: $collection})",
      { params: { value, user, collection } },
    );
  });

  const relateNode = Effect.fn("FalkorDBTriplesStore.relateNode")(function* (
    src: string,
    uri: string,
    dest: string,
    user: string,
    collection: string,
  ) {
    const { graph } = yield* getConnection();
    yield* runGraphQuery(
      graph,
      "relate-node",
      "MATCH (src:Node {uri: $src, user: $user, collection: $collection}) " +
        "MATCH (dest:Node {uri: $dest, user: $user, collection: $collection}) " +
        "MERGE (src)-[:Rel {uri: $uri, user: $user, collection: $collection}]->(dest)",
      { params: { src, dest, uri, user, collection } },
    );
  });

  const relateLiteral = Effect.fn("FalkorDBTriplesStore.relateLiteral")(function* (
    src: string,
    uri: string,
    dest: string,
    user: string,
    collection: string,
  ) {
    const { graph } = yield* getConnection();
    yield* runGraphQuery(
      graph,
      "relate-literal",
      "MATCH (src:Node {uri: $src, user: $user, collection: $collection}) " +
        "MATCH (dest:Literal {value: $dest, user: $user, collection: $collection}) " +
        "MERGE (src)-[:Rel {uri: $uri, user: $user, collection: $collection}]->(dest)",
      { params: { src, dest, uri, user, collection } },
    );
  });

  const storeTriples = Effect.fn("FalkorDBTriplesStore.storeTriples")(function* (
    triples: ReadonlyArray<Triple>,
    user: string,
    collection: string,
  ) {
    for (const triple of triples) {
      const s = getTermValue(triple.s);
      const p = getTermValue(triple.p);
      const o = getTermValue(triple.o);

      yield* createNode(s, user, collection);

      if (triple.o.type === "IRI") {
        yield* createNode(o, user, collection);
        yield* relateNode(s, p, o, user, collection);
      } else {
        yield* createLiteral(o, user, collection);
        yield* relateLiteral(s, p, o, user, collection);
      }
    }
  });

  const deleteCollection = Effect.fn("FalkorDBTriplesStore.deleteCollection")(function* (
    user: string,
    collection: string,
  ) {
    const { graph } = yield* getConnection();
    yield* runGraphQuery(
      graph,
      "delete-collection-nodes",
      "MATCH (n:Node {user: $user, collection: $collection}) DETACH DELETE n",
      { params: { user, collection } },
    );
    yield* runGraphQuery(
      graph,
      "delete-collection-literals",
      "MATCH (n:Literal {user: $user, collection: $collection}) DETACH DELETE n",
      { params: { user, collection } },
    );
    yield* runGraphQuery(
      graph,
      "delete-collection-metadata",
      "MATCH (c:CollectionMetadata {user: $user, collection: $collection}) DELETE c",
      { params: { user, collection } },
    );
  });

  return {
    createNode,
    createLiteral,
    relateNode,
    relateLiteral,
    storeTriples,
    deleteCollection,
  };
};

export function makeFalkorDBTriplesStore(config: FalkorDBConfig = {}): FalkorDBTriplesStore {
  const store = makeFalkorDBTriplesStoreEffect(config);
  return {
    createNode: (uri, user, collection) =>
      Effect.runPromise(store.createNode(uri, user, collection)),
    createLiteral: (value, user, collection) =>
      Effect.runPromise(store.createLiteral(value, user, collection)),
    relateNode: (src, uri, dest, user, collection) =>
      Effect.runPromise(store.relateNode(src, uri, dest, user, collection)),
    relateLiteral: (src, uri, dest, user, collection) =>
      Effect.runPromise(store.relateLiteral(src, uri, dest, user, collection)),
    storeTriples: (triples, user = "default", collection = "default") =>
      Effect.runPromise(store.storeTriples(triples, user, collection)),
    deleteCollection: (user, collection) =>
      Effect.runPromise(store.deleteCollection(user, collection)),
  };
}

export const makeFalkorDBTriplesStoreService = (
  config: FalkorDBConfig = {},
): FalkorDBTriplesStoreServiceShape => {
  const store = makeFalkorDBTriplesStoreEffect(config);
  return {
    storeTriples: store.storeTriples,
    deleteCollection: store.deleteCollection,
  };
};

export const FalkorDBTriplesStoreLive = (
  config: FalkorDBConfig = {},
): Layer.Layer<FalkorDBTriplesStoreService> =>
  Layer.succeed(
    FalkorDBTriplesStoreService,
    FalkorDBTriplesStoreService.of(makeFalkorDBTriplesStoreService(config)),
  );
