/**
 * FalkorDB triples store — writes RDF triples to a FalkorDB graph.
 *
 * FalkorDB is Redis-based and uses Cypher queries, same as the Python impl.
 * Pairs well with Graphiti which also uses FalkorDB as its backend.
 *
 * Python reference: trustgraph-flow/trustgraph/storage/triples/falkordb/write.py
 */

import { createClient, Graph } from "falkordb";
import { errorMessage, type Term, type Triple } from "@trustgraph/base";
import { Context, Effect, Layer } from "effect";
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
      return getTermValue(term.triple.s); // fallback
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

export function makeFalkorDBTriplesStore(config: FalkorDBConfig = {}): FalkorDBTriplesStore {
  const url = config.url ?? process.env.FALKORDB_URL ?? "redis://localhost:6379";
  const database = config.database ?? "falkordb";

  const client = createClient({ url });
  const graph = new Graph(client, database);
  const connectPromise = client.connect().then(() => {
    console.log(`[FalkorDBTriplesStore] Connected to ${url}, graph: ${database}`);
  }).catch((err) => {
    console.error(`[FalkorDBTriplesStore] Connection failed:`, err);
    throw err;
  });

  const ensureConnected = async (): Promise<void> => {
    await connectPromise;
  };

  const createNode = async (uri: string, user: string, collection: string): Promise<void> => {
    await ensureConnected();
    await graph.query(
      "MERGE (n:Node {uri: $uri, user: $user, collection: $collection})",
      { params: { uri, user, collection } },
    );
  };

  const createLiteral = async (value: string, user: string, collection: string): Promise<void> => {
    await ensureConnected();
    await graph.query(
      "MERGE (n:Literal {value: $value, user: $user, collection: $collection})",
      { params: { value, user, collection } },
    );
  };

  const relateNode = async (
    src: string, uri: string, dest: string,
    user: string, collection: string,
  ): Promise<void> => {
    await ensureConnected();
    await graph.query(
      "MATCH (src:Node {uri: $src, user: $user, collection: $collection}) " +
      "MATCH (dest:Node {uri: $dest, user: $user, collection: $collection}) " +
      "MERGE (src)-[:Rel {uri: $uri, user: $user, collection: $collection}]->(dest)",
      { params: { src, dest, uri, user, collection } },
    );
  };

  const relateLiteral = async (
    src: string, uri: string, dest: string,
    user: string, collection: string,
  ): Promise<void> => {
    await ensureConnected();
    await graph.query(
      "MATCH (src:Node {uri: $src, user: $user, collection: $collection}) " +
      "MATCH (dest:Literal {value: $dest, user: $user, collection: $collection}) " +
      "MERGE (src)-[:Rel {uri: $uri, user: $user, collection: $collection}]->(dest)",
      { params: { src, dest, uri, user, collection } },
    );
  };

  const storeTriples = async (
    triples: Triple[],
    user = "default",
    collection = "default",
  ): Promise<void> => {
    for (const t of triples) {
      const s = getTermValue(t.s);
      const p = getTermValue(t.p);
      const o = getTermValue(t.o);

      await createNode(s, user, collection);

      if (t.o.type === "IRI") {
        await createNode(o, user, collection);
        await relateNode(s, p, o, user, collection);
      } else {
        await createLiteral(o, user, collection);
        await relateLiteral(s, p, o, user, collection);
      }
    }
  };

  const deleteCollection = async (user: string, collection: string): Promise<void> => {
    await ensureConnected();
    await graph.query(
      "MATCH (n:Node {user: $user, collection: $collection}) DETACH DELETE n",
      { params: { user, collection } },
    );
    await graph.query(
      "MATCH (n:Literal {user: $user, collection: $collection}) DETACH DELETE n",
      { params: { user, collection } },
    );
    await graph.query(
      "MATCH (c:CollectionMetadata {user: $user, collection: $collection}) DELETE c",
      { params: { user, collection } },
    );
  };

  return {
    createNode,
    createLiteral,
    relateNode,
    relateLiteral,
    storeTriples,
    deleteCollection,
  };
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

const falkorDBTriplesStoreError = (operation: string, cause: unknown) =>
  new FalkorDBTriplesStoreError({
    operation,
    message: errorMessage(cause),
    cause,
  });

export const makeFalkorDBTriplesStoreService = (
  config: FalkorDBConfig = {},
): FalkorDBTriplesStoreServiceShape => {
  const store = makeFalkorDBTriplesStore(config);
  return {
    storeTriples: Effect.fn("FalkorDBTriplesStore.storeTriples")((
      triples: ReadonlyArray<Triple>,
      user: string,
      collection: string,
    ) =>
      Effect.tryPromise({
        try: () => store.storeTriples(Array.from(triples), user, collection),
        catch: (cause) => falkorDBTriplesStoreError("store-triples", cause),
      })),
    deleteCollection: Effect.fn("FalkorDBTriplesStore.deleteCollection")((
      user: string,
      collection: string,
    ) =>
      Effect.tryPromise({
        try: () => store.deleteCollection(user, collection),
        catch: (cause) => falkorDBTriplesStoreError("delete-collection", cause),
      })),
  };
};

export const FalkorDBTriplesStoreLive = (
  config: FalkorDBConfig = {},
): Layer.Layer<FalkorDBTriplesStoreService> =>
  Layer.succeed(
    FalkorDBTriplesStoreService,
    FalkorDBTriplesStoreService.of(makeFalkorDBTriplesStoreService(config)),
  );
