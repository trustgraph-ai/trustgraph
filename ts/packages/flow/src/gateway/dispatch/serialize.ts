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

import type { Term, Triple } from "@trustgraph/base";
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

interface ClientTriple {
  s: ClientTerm;
  p: ClientTerm;
  o: ClientTerm;
  g?: string;
}

// ---------- Client → Internal ----------

export function clientTermToInternal(wire: ClientTerm): Term {
  switch (wire.t) {
    case "i":
      return { type: "IRI", iri: wire.i };
    case "b":
      return { type: "BLANK", id: wire.d };
    case "l":
      return {
        type: "LITERAL",
        value: wire.v,
        ...(wire.dt !== undefined ? { datatype: wire.dt } : {}),
        ...(wire.ln !== undefined ? { language: wire.ln } : {}),
      };
    case "t": {
      if (wire.tr === undefined) {
        throw DispatchSerializationError.make({
          operation: "client-term-to-internal",
          message: "Client triple term is missing tr",
        });
      }
      return {
        type: "TRIPLE",
        triple: clientTripleToInternal(wire.tr),
      };
    }
    default:
      // Defensive: pass through unknown term types
      return wire as unknown as Term;
  }
}

export function clientTripleToInternal(wire: ClientTriple): Triple {
  const result: Triple = {
    s: clientTermToInternal(wire.s),
    p: clientTermToInternal(wire.p),
    o: clientTermToInternal(wire.o),
  };
  if (wire.g !== undefined) {
    // In the client wire format, g is a plain string.
    // In the internal format, g is an optional Term (named graph).
    // The Python translator treats g as a plain string passthrough,
    // so we keep it as-is for compatibility.
    (result as unknown as Record<string, unknown>).g = wire.g;
  }
  return result;
}

// ---------- Internal → Client ----------

export function internalTermToClient(term: Term): ClientTerm {
  switch (term.type) {
    case "IRI":
      return { t: "i", i: term.iri };
    case "BLANK":
      return { t: "b", d: term.id };
    case "LITERAL": {
      const lit: ClientLiteralTerm = { t: "l", v: term.value };
      if (term.datatype !== undefined) lit.dt = term.datatype;
      if (term.language !== undefined) lit.ln = term.language;
      return lit;
    }
    case "TRIPLE":
      return {
        t: "t",
        tr: internalTripleToClient(term.triple),
      };
    default:
      return term as unknown as ClientTerm;
  }
}

export function internalTripleToClient(triple: Triple): ClientTriple {
  const result: ClientTriple = {
    s: internalTermToClient(triple.s),
    p: internalTermToClient(triple.p),
    o: internalTermToClient(triple.o),
  };
  const g = (triple as unknown as Record<string, unknown>).g;
  if (g !== undefined && g !== null) {
    if (typeof g === "string") {
      result.g = g;
    } else {
      // If g is a Term, convert it back to client wire format
      const iri = (g as Record<string, unknown>).iri;
      if (typeof iri === "string") {
        result.g = iri;
      }
    }
  }
  return result;
}

// ---------- Deep object translation ----------

/**
 * Recursively walk an object and translate every Term-shaped value.
 * A client term is detected by the presence of a `t` property
 * with value "i", "b", "l", or "t".
 */
function isClientTerm(v: unknown): v is ClientTerm {
  return (
    typeof v === "object" &&
    v !== null &&
    "t" in v &&
    typeof (v as Record<string, unknown>).t === "string" &&
    ["i", "b", "l", "t"].includes((v as Record<string, unknown>).t as string)
  );
}

/**
 * An internal term is detected by the presence of a `type` property
 * with value "IRI", "BLANK", "LITERAL", or "TRIPLE".
 */
function isInternalTerm(v: unknown): v is Term {
  return (
    typeof v === "object" &&
    v !== null &&
    "type" in v &&
    typeof (v as Record<string, unknown>).type === "string" &&
    ["IRI", "BLANK", "LITERAL", "TRIPLE"].includes(
      (v as Record<string, unknown>).type as string,
    )
  );
}

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
    if (isClientTerm(value)) {
      return clientTermToInternal(value);
    }
    const result: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
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
    if (isInternalTerm(value)) {
      return internalTermToClient(value);
    }
    const result: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
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
