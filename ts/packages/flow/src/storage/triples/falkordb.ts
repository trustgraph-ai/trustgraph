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
import { Config, Context, Effect, Layer, Match } from "effect";
import * as S from "effect/Schema";

export interface FalkorDBClosableClient {
  readonly connect: () => Promise<unknown>;
  readonly disconnect: () => Promise<unknown>;
}

export type FalkorDBStoreQueryOptions = Parameters<Graph["query"]>[1];

export interface FalkorDBStoreGraph {
  readonly query: <T = unknown>(
    query: string,
    options?: FalkorDBStoreQueryOptions,
  ) => Promise<{ readonly data?: Array<T> }>;
}

export type FalkorDBStoreClientFactory = (url: string) => FalkorDBClosableClient;
export type FalkorDBStoreGraphFactory = (
  client: FalkorDBClosableClient,
  database: string,
) => FalkorDBStoreGraph;

export interface FalkorDBConfig {
  url?: string;
  database?: string;
  clientFactory?: FalkorDBStoreClientFactory;
  graphFactory?: FalkorDBStoreGraphFactory;
}

function getTermValue(term: Term): string {
  return Match.type<Term>().pipe(
    Match.discriminatorsExhaustive("type")({
      IRI: (iri) => iri.iri,
      LITERAL: (literal) => literal.value,
      BLANK: (blank) => blank.id,
      TRIPLE: (triple) => getTermValue(triple.triple.s),
    }),
  )(term);
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
  readonly client: FalkorDBClosableClient;
  readonly graph: FalkorDBStoreGraph;
}

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

const connectFalkorDBTriplesStore = Effect.fn("FalkorDBTriplesStore.connect")(function* (
  config: FalkorDBConfig,
) {
    const { url, database } = yield* resolveFalkorDBStoreConfig(config);
    const clientFactory = config.clientFactory;
    const graphFactory = config.graphFactory;

    if (
      (clientFactory === undefined && graphFactory !== undefined) ||
      (clientFactory !== undefined && graphFactory === undefined)
    ) {
      return yield* falkorDBTriplesStoreError(
        "create-client",
        "FalkorDB custom clientFactory and graphFactory must be configured together",
      );
    }

    const { client, graph } = yield* Effect.try({
      try: () => {
        if (clientFactory !== undefined && graphFactory !== undefined) {
          const client = clientFactory(url);
          return { client, graph: graphFactory(client, database) };
        }
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
    return { client, graph };
  });

const disconnectFalkorDBTriplesStore = (
  connection: FalkorDBStoreConnection,
): Effect.Effect<void> =>
  Effect.tryPromise({
    try: () => connection.client.disconnect(),
    catch: (cause) => falkorDBTriplesStoreError("disconnect", cause),
  }).pipe(
    Effect.catch((error) =>
      Effect.logError("[FalkorDBTriplesStore] Disconnect failed", {
        error: error.message,
        operation: error.operation,
      }),
    ),
    Effect.asVoid,
  );

const acquireFalkorDBTriplesStore = (
  config: FalkorDBConfig,
) =>
  Effect.acquireRelease(
    connectFalkorDBTriplesStore(config),
    (connection) => disconnectFalkorDBTriplesStore(connection),
  );

const runGraphQuery = (
  graph: FalkorDBStoreGraph,
  operation: string,
  query: string,
  options?: FalkorDBStoreQueryOptions,
): Effect.Effect<void, FalkorDBTriplesStoreError> =>
  Effect.tryPromise({
    try: () => graph.query(query, options),
    catch: (cause) => falkorDBTriplesStoreError(operation, cause),
  }).pipe(
    Effect.asVoid,
  );

const makeFalkorDBTriplesStoreEffect = (
  getConnection: () => Effect.Effect<FalkorDBStoreConnection, FalkorDBTriplesStoreError>,
): FalkorDBTriplesStoreEffectShape => {
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

const makeFalkorDBTriplesStoreEffectScoped = (
  config: FalkorDBConfig = {},
) =>
  acquireFalkorDBTriplesStore(config).pipe(
    Effect.map((connection) => makeFalkorDBTriplesStoreEffect(() => Effect.succeed(connection))),
  );

const withFalkorDBTriplesStore = <A>(
  config: FalkorDBConfig,
  use: (store: FalkorDBTriplesStoreEffectShape) => Effect.Effect<A, FalkorDBTriplesStoreError>,
) =>
  Effect.scoped(
    makeFalkorDBTriplesStoreEffectScoped(config).pipe(
      Effect.flatMap(use),
    ),
  );

export function makeFalkorDBTriplesStore(config: FalkorDBConfig = {}): FalkorDBTriplesStore {
  return {
    createNode: (uri, user, collection) =>
      Effect.runPromise(withFalkorDBTriplesStore(config, (store) => store.createNode(uri, user, collection))),
    createLiteral: (value, user, collection) =>
      Effect.runPromise(withFalkorDBTriplesStore(config, (store) => store.createLiteral(value, user, collection))),
    relateNode: (src, uri, dest, user, collection) =>
      Effect.runPromise(withFalkorDBTriplesStore(config, (store) => store.relateNode(src, uri, dest, user, collection))),
    relateLiteral: (src, uri, dest, user, collection) =>
      Effect.runPromise(withFalkorDBTriplesStore(config, (store) => store.relateLiteral(src, uri, dest, user, collection))),
    storeTriples: (triples, user = "default", collection = "default") =>
      Effect.runPromise(withFalkorDBTriplesStore(config, (store) => store.storeTriples(triples, user, collection))),
    deleteCollection: (user, collection) =>
      Effect.runPromise(withFalkorDBTriplesStore(config, (store) => store.deleteCollection(user, collection))),
  };
}

export const makeFalkorDBTriplesStoreService = (
  config: FalkorDBConfig = {},
): FalkorDBTriplesStoreServiceShape => ({
  storeTriples: (triples, user, collection) =>
    withFalkorDBTriplesStore(config, (store) => store.storeTriples(triples, user, collection)),
  deleteCollection: (user, collection) =>
    withFalkorDBTriplesStore(config, (store) => store.deleteCollection(user, collection)),
});

export const makeFalkorDBTriplesStoreServiceFromConnection = (
  connection: FalkorDBStoreConnection,
): FalkorDBTriplesStoreServiceShape => {
  const store = makeFalkorDBTriplesStoreEffect(() => Effect.succeed(connection));
  return {
    storeTriples: store.storeTriples,
    deleteCollection: store.deleteCollection,
  };
};

export const makeFalkorDBTriplesStoreServiceScoped = (
  config: FalkorDBConfig = {},
) =>
  makeFalkorDBTriplesStoreEffectScoped(config).pipe(
    Effect.map((store) => ({
      storeTriples: store.storeTriples,
      deleteCollection: store.deleteCollection,
    })),
  );

export const FalkorDBTriplesStoreLive = (
  config: FalkorDBConfig = {},
): Layer.Layer<FalkorDBTriplesStoreService, FalkorDBTriplesStoreError> =>
  Layer.effect(
    FalkorDBTriplesStoreService,
    makeFalkorDBTriplesStoreServiceScoped(config).pipe(
      Effect.map((service) => FalkorDBTriplesStoreService.of(service)),
    ),
  );
