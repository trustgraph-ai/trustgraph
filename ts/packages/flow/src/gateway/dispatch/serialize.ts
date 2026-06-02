/**
 * Wire format serializer — translates between the compact client wire format
 * (used by @trustgraph/client) and the verbose internal format
 * (used by @trustgraph/base services).
 *
 * Client wire format (compact):
 *   IRI:     { t: "i", i: "<iri>" }
 *   BLANK:   { t: "b", d: "<id>" }
 *   LITERAL: { t: "l", v: "<value>", dt?: "<datatype>", ln?: "<language>" }
 *   TRIPLE:  { t: "t", tr?: { s, p, o, g? } }
 *
 * Internal format (verbose):
 *   IRI:     { type: "IRI", iri: "<iri>" }
 *   BLANK:   { type: "BLANK", id: "<id>" }
 *   LITERAL: { type: "LITERAL", value: "<value>", datatype?: "<dt>", language?: "<lang>" }
 *   TRIPLE:  { type: "TRIPLE", triple: { s, p, o, g? } }
 *
 * Python reference: trustgraph-base/trustgraph/messaging/translators/primitives.py
 */

import {
  BlankTerm,
  errorMessage,
  IriTerm,
  LiteralTerm,
  Term as TermSchema,
  Triple as TripleSchema,
  TripleTerm,
  type Term,
  type Triple,
} from "@trustgraph/base";
import { Effect, Match } from "effect";
import * as O from "effect/Option";
import * as S from "effect/Schema";

// ---------- Client wire format type definitions ----------

interface ClientIriTerm {
  t: "i";
  i: string;
}

interface ClientBlankTerm {
  t: "b";
  d: string;
}

interface ClientLiteralTerm {
  t: "l";
  v: string;
  dt?: string;
  ln?: string;
}

interface ClientTripleTerm {
  t: "t";
  tr?: ClientTriple;
}

type ClientTerm = ClientIriTerm | ClientBlankTerm | ClientLiteralTerm | ClientTripleTerm;

export class DispatchSerializationError extends S.TaggedErrorClass<DispatchSerializationError>()(
  "DispatchSerializationError",
  {
    message: S.String,
    operation: S.String,
  },
) {}

const isDispatchSerializationError = S.is(DispatchSerializationError);

interface ClientTriple {
  s: ClientTerm;
  p: ClientTerm;
  o: ClientTerm;
  g?: string;
}

const ClientIriTermSchema = S.Struct({
  t: S.tag("i"),
  i: S.String,
});

const ClientBlankTermSchema = S.Struct({
  t: S.tag("b"),
  d: S.String,
});

const ClientLiteralTermSchema = S.Struct({
  t: S.tag("l"),
  v: S.String,
  dt: S.optionalKey(S.String),
  ln: S.optionalKey(S.String),
});

const ClientTripleSchema: S.Codec<ClientTriple, ClientTriple> = S.Struct({
  s: S.suspend((): S.Codec<ClientTerm, ClientTerm> => ClientTermSchema),
  p: S.suspend((): S.Codec<ClientTerm, ClientTerm> => ClientTermSchema),
  o: S.suspend((): S.Codec<ClientTerm, ClientTerm> => ClientTermSchema),
  g: S.optionalKey(S.String),
});

const ClientTripleTermSchema = S.Struct({
  t: S.tag("t"),
  tr: S.optionalKey(ClientTripleSchema),
});

const ClientTermSchema = S.Union([
  ClientIriTermSchema,
  ClientBlankTermSchema,
  ClientLiteralTermSchema,
  ClientTripleTermSchema,
]).pipe(S.toTaggedUnion("t"));

const decodeClientTerm = S.decodeUnknownOption(ClientTermSchema);
const decodeInternalTerm = S.decodeUnknownOption(TermSchema);

const clientTermToInternalMatch = Match.type<ClientTerm>().pipe(
  Match.discriminatorsExhaustive("t")({
    i: (wire) => IriTerm.make({ iri: wire.i }),
    b: (wire) => BlankTerm.make({ id: wire.d }),
    l: (wire) => LiteralTerm.make({
      value: wire.v,
      ...(wire.dt !== undefined ? { datatype: wire.dt } : {}),
      ...(wire.ln !== undefined ? { language: wire.ln } : {}),
    }),
    t: (wire) => {
      if (wire.tr === undefined) {
        throw DispatchSerializationError.make({
          operation: "client-term-to-internal",
          message: "Client triple term is missing tr",
        });
      }
      return TripleTerm.make({
        triple: clientTripleToInternal(wire.tr),
      });
    },
  }),
);

const internalTermToClientMatch = Match.type<Term>().pipe(
  Match.discriminatorsExhaustive("type")({
    IRI: (term) => ClientIriTermSchema.make({ i: term.iri }),
    BLANK: (term) => ClientBlankTermSchema.make({ d: term.id }),
    LITERAL: (term) => ClientLiteralTermSchema.make({
      v: term.value,
      ...(term.datatype !== undefined ? { dt: term.datatype } : {}),
      ...(term.language !== undefined ? { ln: term.language } : {}),
    }),
    TRIPLE: (term) => ClientTripleTermSchema.make({
      tr: internalTripleToClient(term.triple),
    }),
  }),
);

// ---------- Client → Internal ----------

export function clientTermToInternal(wire: ClientTerm): Term {
  return clientTermToInternalMatch(wire);
}

export function clientTripleToInternal(wire: ClientTriple): Triple {
  return TripleSchema.make({
    s: clientTermToInternal(wire.s),
    p: clientTermToInternal(wire.p),
    o: clientTermToInternal(wire.o),
    ...(wire.g !== undefined ? { g: wire.g } : {}),
  });
}

// ---------- Internal → Client ----------

export function internalTermToClient(term: Term): ClientTerm {
  return internalTermToClientMatch(term);
}

export function internalTripleToClient(triple: Triple): ClientTriple {
  const result: ClientTriple = {
    s: internalTermToClient(triple.s),
    p: internalTermToClient(triple.p),
    o: internalTermToClient(triple.o),
  };
  if (triple.g !== undefined) {
    result.g = triple.g;
  }
  return result;
}

// ---------- Deep object translation ----------

/**
 * Recursively walk an object and translate every Term-shaped value.
 * A client term is detected by the presence of a `t` property
 * with value "i", "b", "l", or "t".
 */
/**
 * Deep-translate all client Terms in a request body to internal format.
 * Handles nested objects and arrays.
 */
function deepClientToInternal(value: unknown): unknown {
  if (value === null || value === undefined) return value;

  if (Array.isArray(value)) {
    return value.map(deepClientToInternal);
  }

  if (typeof value === "object") {
    const term = decodeClientTerm(value);
    if (O.isSome(term)) {
      return clientTermToInternal(term.value);
    }
    const result: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(value)) {
      result[k] = deepClientToInternal(v);
    }
    return result;
  }

  return value;
}

/**
 * Deep-translate all internal Terms in a response body to client format.
 * Handles nested objects and arrays.
 */
function deepInternalToClient(value: unknown): unknown {
  if (value === null || value === undefined) return value;

  if (Array.isArray(value)) {
    return value.map(deepInternalToClient);
  }

  if (typeof value === "object") {
    const term = decodeInternalTerm(value);
    if (O.isSome(term)) {
      return internalTermToClient(term.value);
    }
    const result: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(value)) {
      result[k] = deepInternalToClient(v);
    }
    return result;
  }

  return value;
}

// ---------- Services that contain Term fields ----------

/**
 * Services whose requests contain Term/Triple fields that need translation.
 * All other services pass through without term translation.
 */
const TERM_BEARING_REQUEST_SERVICES = new Set([
  "triples",
  "knowledge",
  "librarian",
]);

/**
 * Services whose responses contain Term/Triple fields that need translation.
 */
const TERM_BEARING_RESPONSE_SERVICES = new Set([
  "triples",
  "graph-embeddings",
  "knowledge",
  "librarian",
  "graph-rag",
  "agent",
]);

// ---------- Top-level request / response translators ----------

/**
 * Translate a client request body to internal format.
 *
 * For services that carry Term fields (triples, knowledge), this deep-walks
 * the request and converts compact → verbose.
 * All other services pass through unchanged, since their payloads are simple
 * scalar fields (query strings, limits, etc.).
 */
export function translateRequest(service: string, body: unknown): unknown {
  if (TERM_BEARING_REQUEST_SERVICES.has(service)) {
    return deepClientToInternal(body);
  }
  return body;
}

export const translateRequestEffect = (
  service: string,
  body: unknown,
): Effect.Effect<unknown, DispatchSerializationError> =>
  Effect.try({
    try: () => translateRequest(service, body),
    catch: (cause) =>
      isDispatchSerializationError(cause)
        ? cause
        : DispatchSerializationError.make({
            operation: `translate-request:${service}`,
            message: errorMessage(cause),
          }),
  });

/**
 * Translate an internal response body to client wire format.
 *
 * For services that return Term fields (triples, graph-embeddings, knowledge),
 * this deep-walks the response and converts verbose → compact.
 * All other services pass through unchanged.
 */
export function translateResponse(service: string, response: unknown): unknown {
  if (TERM_BEARING_RESPONSE_SERVICES.has(service)) {
    return deepInternalToClient(response);
  }
  return response;
}

export const translateResponseEffect = (
  service: string,
  response: unknown,
): Effect.Effect<unknown, DispatchSerializationError> =>
  Effect.try({
    try: () => translateResponse(service, response),
    catch: (cause) =>
      isDispatchSerializationError(cause)
        ? cause
        : DispatchSerializationError.make({
            operation: `translate-response:${service}`,
            message: errorMessage(cause),
          }),
  });
