/**
 * FalkorDB triples query service - queries RDF triples from FalkorDB.
 *
 * Implements all SPO query patterns (S, P, O, SP, SO, PO, SPO, *).
 *
 * Python reference: trustgraph-flow/trustgraph/query/triples/falkordb/service.py
 */

import { createClient, Graph } from "falkordb";
import { errorMessage, type Term, type Triple } from "@trustgraph/base";
import { Config, Context, Effect, Layer, Match } from "effect";
import * as Predicate from "effect/Predicate";
import * as S from "effect/Schema";

export interface FalkorDBClosableClient {
  readonly connect: () => Promise<unknown>;
  readonly disconnect: () => Promise<unknown>;
}

export type FalkorDBQueryOptions = Parameters<Graph["query"]>[1];

export interface FalkorDBQueryGraph {
  readonly query: <T = unknown>(
    query: string,
    options?: FalkorDBQueryOptions,
  ) => Promise<{ readonly data?: Array<T> }>;
}

export type FalkorDBQueryClientFactory = (url: string) => FalkorDBClosableClient;
export type FalkorDBQueryGraphFactory = (
  client: FalkorDBClosableClient,
  database: string,
) => FalkorDBQueryGraph;

export interface FalkorDBQueryConfig {
  url?: string;
  database?: string;
  clientFactory?: FalkorDBQueryClientFactory;
  graphFactory?: FalkorDBQueryGraphFactory;
}

function termToValue(term: Term | undefined): string | null {
  if (term === undefined) return null;
  return Match.type<Term>().pipe(
    Match.discriminatorsExhaustive("type")({
      IRI: (iri) => iri.iri,
      LITERAL: (literal) => literal.value,
      BLANK: (blank) => blank.id,
      TRIPLE: () => null,
    }),
  )(term);
}

function createTerm(value: string): Term {
  if (value.length === 0) {
    return { type: "LITERAL", value: "" };
  }
  if (value.startsWith("http://") || value.startsWith("https://")) {
    return { type: "IRI", iri: value };
  }
  return { type: "LITERAL", value };
}

function field(row: unknown, key: string): string {
  if (!Predicate.hasProperty(row, key)) return "";
  const value = row[key];
  return typeof value === "string" ? value : "";
}

export interface FalkorDBTriplesQuery {
  readonly queryTriples: (
    s?: Term,
    p?: Term,
    o?: Term,
    limit?: number,
  ) => Promise<Triple[]>;
}

export class FalkorDBTriplesQueryError extends S.TaggedErrorClass<FalkorDBTriplesQueryError>()(
  "FalkorDBTriplesQueryError",
  {
    message: S.String,
    operation: S.String,
    cause: S.DefectWithStack,
  },
) {}

export interface FalkorDBTriplesQueryServiceShape {
  readonly queryTriples: (
    s: Term | undefined,
    p: Term | undefined,
    o: Term | undefined,
    limit: number,
  ) => Effect.Effect<ReadonlyArray<Triple>, FalkorDBTriplesQueryError>;
}

export class FalkorDBTriplesQueryService extends Context.Service<
  FalkorDBTriplesQueryService,
  FalkorDBTriplesQueryServiceShape
>()(
  "@trustgraph/flow/query/triples/falkordb/FalkorDBTriplesQueryService",
) {}

const falkorDBTriplesQueryError = (operation: string, cause: unknown): FalkorDBTriplesQueryError =>
  FalkorDBTriplesQueryError.make({
    operation,
    message: errorMessage(cause),
    cause,
  });

interface FalkorDBQueryConnection {
  readonly client: FalkorDBClosableClient;
  readonly graph: FalkorDBQueryGraph;
}

const resolveFalkorDBQueryConfig = Effect.fn("FalkorDBTriplesQuery.resolveConfig")(function* (
  config: FalkorDBQueryConfig,
) {
  const url = config.url ?? (yield* Config.string("FALKORDB_URL").pipe(
    Config.withDefault("redis://localhost:6379"),
    Effect.mapError((cause) => falkorDBTriplesQueryError("config", cause)),
  ));
  return {
    url,
    database: config.database ?? "falkordb",
  };
});

const connectFalkorDBTriplesQuery = Effect.fn("FalkorDBTriplesQuery.connect")(function* (
  config: FalkorDBQueryConfig,
) {
    const { url, database } = yield* resolveFalkorDBQueryConfig(config);
    const clientFactory = config.clientFactory;
    const graphFactory = config.graphFactory;

    if (
      (clientFactory === undefined && graphFactory !== undefined) ||
      (clientFactory !== undefined && graphFactory === undefined)
    ) {
      return yield* falkorDBTriplesQueryError(
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
      catch: (cause) => falkorDBTriplesQueryError("create-client", cause),
    });

    yield* Effect.tryPromise({
      try: () => client.connect(),
      catch: (cause) => falkorDBTriplesQueryError("connect", cause),
    }).pipe(
      Effect.tapError((error) =>
        Effect.logError("[FalkorDBTriplesQuery] Connection failed", {
          error: error.message,
          operation: error.operation,
        })
      ),
    );

    yield* Effect.log(`[FalkorDBTriplesQuery] Connected to ${url}, graph: ${database}`);
    return { client, graph };
  });

const disconnectFalkorDBTriplesQuery = (
  connection: FalkorDBQueryConnection,
): Effect.Effect<void> =>
  Effect.tryPromise({
    try: () => connection.client.disconnect(),
    catch: (cause) => falkorDBTriplesQueryError("disconnect", cause),
  }).pipe(
    Effect.catch((error) =>
      Effect.logError("[FalkorDBTriplesQuery] Disconnect failed", {
        error: error.message,
        operation: error.operation,
      }),
    ),
    Effect.asVoid,
  );

const acquireFalkorDBTriplesQuery = (
  config: FalkorDBQueryConfig,
) =>
  Effect.acquireRelease(
    connectFalkorDBTriplesQuery(config),
    (connection) => disconnectFalkorDBTriplesQuery(connection),
  );

const queryRows = (
  graph: FalkorDBQueryGraph,
  operation: string,
  query: string,
  options?: FalkorDBQueryOptions,
): Effect.Effect<ReadonlyArray<unknown>, FalkorDBTriplesQueryError> =>
  Effect.tryPromise({
    try: () => graph.query<unknown>(query, options),
    catch: (cause) => falkorDBTriplesQueryError(operation, cause),
  }).pipe(
    Effect.map((result) => result.data ?? []),
  );

const matchPattern = Effect.fnUntraced(function* (
  graph: FalkorDBQueryGraph,
  out: [string, string, string][],
  sv: string,
  pv: string,
  ov: string,
  limit: number,
) {
    for (const destType of ["Literal", "Node"] as const) {
      const destKey = destType === "Literal" ? "value" : "uri";
      const rows = yield* queryRows(
        graph,
        "match-spo",
        `MATCH (src:Node {uri: $src})-[rel:Rel {uri: $rel}]->(dest:${destType} {${destKey}: $dest}) ` +
          `RETURN src.uri LIMIT ${limit}`,
        { params: { src: sv, rel: pv, dest: ov } },
      );
      for (const _rec of rows) {
        out.push([sv, pv, ov]);
      }
    }
  });

const matchSP = Effect.fnUntraced(function* (
  graph: FalkorDBQueryGraph,
  out: [string, string, string][],
  sv: string,
  pv: string,
  limit: number,
) {
    const litRows = yield* queryRows(
      graph,
      "match-sp-literal",
      `MATCH (src:Node {uri: $src})-[rel:Rel {uri: $rel}]->(dest:Literal) ` +
        `RETURN dest.value as dest LIMIT ${limit}`,
      { params: { src: sv, rel: pv } },
    );
    for (const rec of litRows) {
      out.push([sv, pv, field(rec, "dest")]);
    }

    const nodeRows = yield* queryRows(
      graph,
      "match-sp-node",
      `MATCH (src:Node {uri: $src})-[rel:Rel {uri: $rel}]->(dest:Node) ` +
        `RETURN dest.uri as dest LIMIT ${limit}`,
      { params: { src: sv, rel: pv } },
    );
    for (const rec of nodeRows) {
      out.push([sv, pv, field(rec, "dest")]);
    }
  });

const matchSO = Effect.fnUntraced(function* (
  graph: FalkorDBQueryGraph,
  out: [string, string, string][],
  sv: string,
  ov: string,
  limit: number,
) {
    for (const [destType, destKey] of [["Literal", "value"], ["Node", "uri"]] as const) {
      const rows = yield* queryRows(
        graph,
        "match-so",
        `MATCH (src:Node {uri: $src})-[rel:Rel]->(dest:${destType} {${destKey}: $dest}) ` +
          `RETURN rel.uri as rel LIMIT ${limit}`,
        { params: { src: sv, dest: ov } },
      );
      for (const rec of rows) {
        out.push([sv, field(rec, "rel"), ov]);
      }
    }
  });

const matchPO = Effect.fnUntraced(function* (
  graph: FalkorDBQueryGraph,
  out: [string, string, string][],
  pv: string,
  ov: string,
  limit: number,
) {
    for (const [destType, destKey] of [["Literal", "value"], ["Node", "uri"]] as const) {
      const rows = yield* queryRows(
        graph,
        "match-po",
        `MATCH (src:Node)-[rel:Rel {uri: $rel}]->(dest:${destType} {${destKey}: $dest}) ` +
          `RETURN src.uri as src LIMIT ${limit}`,
        { params: { rel: pv, dest: ov } },
      );
      for (const rec of rows) {
        out.push([field(rec, "src"), pv, ov]);
      }
    }
  });

const matchS = Effect.fnUntraced(function* (
  graph: FalkorDBQueryGraph,
  out: [string, string, string][],
  sv: string,
  limit: number,
) {
    const litRows = yield* queryRows(
      graph,
      "match-s-literal",
      `MATCH (src:Node {uri: $src})-[rel:Rel]->(dest:Literal) ` +
        `RETURN rel.uri as rel, dest.value as dest LIMIT ${limit}`,
      { params: { src: sv } },
    );
    for (const rec of litRows) {
      out.push([sv, field(rec, "rel"), field(rec, "dest")]);
    }

    const nodeRows = yield* queryRows(
      graph,
      "match-s-node",
      `MATCH (src:Node {uri: $src})-[rel:Rel]->(dest:Node) ` +
        `RETURN rel.uri as rel, dest.uri as dest LIMIT ${limit}`,
      { params: { src: sv } },
    );
    for (const rec of nodeRows) {
      out.push([sv, field(rec, "rel"), field(rec, "dest")]);
    }
  });

const matchP = Effect.fnUntraced(function* (
  graph: FalkorDBQueryGraph,
  out: [string, string, string][],
  pv: string,
  limit: number,
) {
    const litRows = yield* queryRows(
      graph,
      "match-p-literal",
      `MATCH (src:Node)-[rel:Rel {uri: $rel}]->(dest:Literal) ` +
        `RETURN src.uri as src, dest.value as dest LIMIT ${limit}`,
      { params: { rel: pv } },
    );
    for (const rec of litRows) {
      out.push([field(rec, "src"), pv, field(rec, "dest")]);
    }

    const nodeRows = yield* queryRows(
      graph,
      "match-p-node",
      `MATCH (src:Node)-[rel:Rel {uri: $rel}]->(dest:Node) ` +
        `RETURN src.uri as src, dest.uri as dest LIMIT ${limit}`,
      { params: { rel: pv } },
    );
    for (const rec of nodeRows) {
      out.push([field(rec, "src"), pv, field(rec, "dest")]);
    }
  });

const matchO = Effect.fnUntraced(function* (
  graph: FalkorDBQueryGraph,
  out: [string, string, string][],
  ov: string,
  limit: number,
) {
    for (const [destType, destKey] of [["Literal", "value"], ["Node", "uri"]] as const) {
      const rows = yield* queryRows(
        graph,
        "match-o",
        `MATCH (src:Node)-[rel:Rel]->(dest:${destType} {${destKey}: $dest}) ` +
          `RETURN src.uri as src, rel.uri as rel LIMIT ${limit}`,
        { params: { dest: ov } },
      );
      for (const rec of rows) {
        out.push([field(rec, "src"), field(rec, "rel"), ov]);
      }
    }
  });

const matchAll = Effect.fnUntraced(function* (
  graph: FalkorDBQueryGraph,
  out: [string, string, string][],
  limit: number,
) {
    const litRows = yield* queryRows(
      graph,
      "match-all-literal",
      `MATCH (src:Node)-[rel:Rel]->(dest:Literal) ` +
        `RETURN src.uri as src, rel.uri as rel, dest.value as dest LIMIT ${limit}`,
    );
    for (const rec of litRows) {
      out.push([field(rec, "src"), field(rec, "rel"), field(rec, "dest")]);
    }

    const nodeRows = yield* queryRows(
      graph,
      "match-all-node",
      `MATCH (src:Node)-[rel:Rel]->(dest:Node) ` +
        `RETURN src.uri as src, rel.uri as rel, dest.uri as dest LIMIT ${limit}`,
    );
    for (const rec of nodeRows) {
      out.push([field(rec, "src"), field(rec, "rel"), field(rec, "dest")]);
    }
  });

const queryTriplesEffect = Effect.fn("FalkorDBTriplesQuery.queryTriplesInternal")(function* (
  getConnection: () => Effect.Effect<FalkorDBQueryConnection, FalkorDBTriplesQueryError>,
  s: Term | undefined,
  p: Term | undefined,
  o: Term | undefined,
  limit: number,
) {
    const { graph } = yield* getConnection();
    const sv = termToValue(s);
    const pv = termToValue(p);
    const ov = termToValue(o);
    const rawTriples: [string, string, string][] = [];

    if (sv !== null && pv !== null && ov !== null) {
      yield* matchPattern(graph, rawTriples, sv, pv, ov, limit);
    } else if (sv !== null && pv !== null) {
      yield* matchSP(graph, rawTriples, sv, pv, limit);
    } else if (sv !== null && ov !== null) {
      yield* matchSO(graph, rawTriples, sv, ov, limit);
    } else if (pv !== null && ov !== null) {
      yield* matchPO(graph, rawTriples, pv, ov, limit);
    } else if (sv !== null) {
      yield* matchS(graph, rawTriples, sv, limit);
    } else if (pv !== null) {
      yield* matchP(graph, rawTriples, pv, limit);
    } else if (ov !== null) {
      yield* matchO(graph, rawTriples, ov, limit);
    } else {
      yield* matchAll(graph, rawTriples, limit);
    }

    return rawTriples
      .slice(0, limit)
      .map(([subject, predicate, object]) => ({
        s: createTerm(subject),
        p: createTerm(predicate),
        o: createTerm(object),
      }));
  });

const makeFalkorDBTriplesQueryEffect = (
  getConnection: () => Effect.Effect<FalkorDBQueryConnection, FalkorDBTriplesQueryError>,
): FalkorDBTriplesQueryServiceShape => ({
  queryTriples: Effect.fn("FalkorDBTriplesQuery.queryTriples")((
    s: Term | undefined,
    p: Term | undefined,
    o: Term | undefined,
    limit: number,
  ) => queryTriplesEffect(getConnection, s, p, o, limit)),
});

const makeFalkorDBTriplesQueryEffectScoped = (
  config: FalkorDBQueryConfig = {},
) =>
  acquireFalkorDBTriplesQuery(config).pipe(
    Effect.map((connection) => makeFalkorDBTriplesQueryEffect(() => Effect.succeed(connection))),
  );

const withFalkorDBTriplesQuery = <A>(
  config: FalkorDBQueryConfig,
  use: (query: FalkorDBTriplesQueryServiceShape) => Effect.Effect<A, FalkorDBTriplesQueryError>,
) =>
  Effect.scoped(
    makeFalkorDBTriplesQueryEffectScoped(config).pipe(
      Effect.flatMap(use),
    ),
  );

export function makeFalkorDBTriplesQuery(
  config: FalkorDBQueryConfig = {},
): FalkorDBTriplesQuery {
  return {
    queryTriples: (s, p, o, limit = 100) =>
      Effect.runPromise(
        withFalkorDBTriplesQuery(config, (query) => query.queryTriples(s, p, o, limit)),
      ).then((triples) => Array.from(triples)),
  };
}

export const makeFalkorDBTriplesQueryService = (
  config: FalkorDBQueryConfig = {},
): FalkorDBTriplesQueryServiceShape => ({
  queryTriples: (s, p, o, limit) =>
    withFalkorDBTriplesQuery(config, (query) => query.queryTriples(s, p, o, limit)),
});

export const makeFalkorDBTriplesQueryServiceFromConnection = (
  connection: FalkorDBQueryConnection,
): FalkorDBTriplesQueryServiceShape =>
  makeFalkorDBTriplesQueryEffect(() => Effect.succeed(connection));

export const makeFalkorDBTriplesQueryServiceScoped = (
  config: FalkorDBQueryConfig = {},
) =>
  makeFalkorDBTriplesQueryEffectScoped(config);

export const FalkorDBTriplesQueryLive = (
  config: FalkorDBQueryConfig = {},
): Layer.Layer<FalkorDBTriplesQueryService, FalkorDBTriplesQueryError> =>
  Layer.effect(
    FalkorDBTriplesQueryService,
    makeFalkorDBTriplesQueryServiceScoped(config).pipe(
      Effect.map((service) => FalkorDBTriplesQueryService.of(service)),
    ),
  );
