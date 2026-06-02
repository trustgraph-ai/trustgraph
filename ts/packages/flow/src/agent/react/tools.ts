/**
 * MVP tools for the ReAct agent.
 *
 * Each tool wraps a RequestResponse client from the flow, providing the agent
 * with access to existing TrustGraph retrieval services.
 */

import type {
  EffectRequestResponse,
  GraphRagRequest,
  GraphRagResponse,
  DocumentRagRequest,
  DocumentRagResponse,
  TriplesQueryRequest,
  TriplesQueryResponse,
  ToolRequest,
  ToolResponse,
  Term,
  Triple,
} from "@trustgraph/base";
import {Term as TermSchema} from "@trustgraph/base";
import { Effect } from "effect";
import * as O from "effect/Option";
import * as Predicate from "effect/Predicate";
import * as S from "effect/Schema";

import type { AgentTool, ToolArg } from "./types.js";

const decodeJsonUnknown = S.decodeUnknownOption(S.UnknownFromJsonString);
const decodeTerm = S.decodeUnknownOption(TermSchema);

/**
 * Format a Term to a human-readable string.
 */
function termToString(term: Term): string {
  switch (term.type) {
    case "IRI":
      return term.iri;
    case "LITERAL":
      return term.value;
    case "BLANK":
      return `_:${term.id}`;
    case "TRIPLE":
      return `(${termToString(term.triple.s)} ${termToString(term.triple.p)} ${termToString(term.triple.o)})`;
  }
}

/**
 * Parse tool input -- accepts either raw JSON or a plain string question.
 */
function parseQuestion(input: string): string {
  const decoded = decodeJsonUnknown(input);
  if (O.isNone(decoded)) return input;

  const parsed = decoded.value;
  if (typeof parsed === "object" && parsed !== null && "question" in parsed) {
    return String(parsed.question);
  }
  if (typeof parsed === "string") {
    return parsed;
  }
  return input;
}

/**
 * Explain data extracted from a graph-rag response.
 */
export interface ExplainData {
  explainId: string;
  triples: Triple[];
}

/**
 * Query the knowledge graph for information about entities and their relationships.
 */
export function createKnowledgeQueryTool(
  client: EffectRequestResponse<GraphRagRequest, GraphRagResponse>,
  collection?: string,
  onExplain?: (data: ExplainData) => void,
): AgentTool {
  return {
    name: "KnowledgeQuery",
    description:
      "Query the knowledge graph for information about entities and their relationships.",
    args: [
      {
        name: "question",
        type: "string",
        description: "The question to ask the knowledge graph",
      },
    ],
    execute: (input: string): Promise<string> => Effect.runPromise(Effect.gen(function* () {
      const question = parseQuestion(input);
      yield* Effect.log(`[KnowledgeQuery] Executing: "${question.slice(0, 60)}..." collection=${collection}`);
      const request: GraphRagRequest = {
        query: question,
        ...(collection !== undefined ? { collection } : {}),
      };
      const res = yield* client.request(request);
      yield* Effect.log(`[KnowledgeQuery] Response (${res.response?.length ?? 0} chars): ${res.error !== undefined ? `ERROR: ${res.error.message}` : `${res.response?.slice(0, 300)}...`}`);

      const explainTriples = res.explain_triples;
      if (res.message_type === "explain" && explainTriples !== undefined && onExplain !== undefined) {
        yield* Effect.sync(() => onExplain({
          explainId: res.explain_id ?? "",
          triples: Array.from(explainTriples),
        }));
      }

      if (res.error !== undefined) return `Error: ${res.error.message}`;
      return res.response;
    })),
  };
}

/**
 * Search documents for relevant information.
 */
export function createDocumentQueryTool(
  client: EffectRequestResponse<DocumentRagRequest, DocumentRagResponse>,
  collection?: string,
): AgentTool {
  return {
    name: "DocumentQuery",
    description:
      "Search the document library for relevant information using semantic search.",
    args: [
      {
        name: "question",
        type: "string",
        description: "The question to search documents for",
      },
    ],
    execute: (input: string): Promise<string> => Effect.runPromise(Effect.gen(function* () {
      const question = parseQuestion(input);
      const request: DocumentRagRequest = {
        query: question,
        ...(collection !== undefined ? { collection } : {}),
      };
      const res = yield* client.request(request);
      if (res.error !== undefined) return `Error: ${res.error.message}`;
      return res.response;
    })),
  };
}

const objectProperty = (value: object, key: string): unknown =>
  Predicate.hasProperty(value, key) ? value[key] : undefined;

const termFromUnknown = (value: unknown): Term | undefined => {
  if (Predicate.isString(value)) {
    return { type: "LITERAL", value };
  }
  const decoded = decodeTerm(value);
  return O.isSome(decoded) ? decoded.value : undefined;
};

/**
 * Parse triples query input. Accepts JSON with optional s, p, o fields.
 */
function parseTriplesInput(input: string): {
  s?: Term;
  p?: Term;
  o?: Term;
  limit?: number;
} {
  const decoded = decodeJsonUnknown(input);
  if (
    O.isNone(decoded) ||
    typeof decoded.value !== "object" ||
    decoded.value === null
  ) {
    return {
      s: { type: "LITERAL", value: input },
    };
  }

  const result: {
    s?: Term;
    p?: Term;
    o?: Term;
    limit?: number;
  } = {};
  const parsed = decoded.value;
  const s = termFromUnknown(objectProperty(parsed, "subject") ?? objectProperty(parsed, "s"));
  const p = termFromUnknown(objectProperty(parsed, "predicate") ?? objectProperty(parsed, "p"));
  const o = termFromUnknown(objectProperty(parsed, "object") ?? objectProperty(parsed, "o"));
  const limit = objectProperty(parsed, "limit");
  if (s !== undefined) result.s = s;
  if (p !== undefined) result.p = p;
  if (o !== undefined) result.o = o;
  if (Predicate.isNumber(limit)) result.limit = limit;
  return result;
}

/**
 * Query for specific triples (subject-predicate-object relationships) in the knowledge graph.
 */
export function createTriplesQueryTool(
  client: EffectRequestResponse<TriplesQueryRequest, TriplesQueryResponse>,
  collection?: string,
): AgentTool {
  return {
    name: "TriplesQuery",
    description:
      "Query for specific triples (subject-predicate-object relationships) in the knowledge graph. " +
      "Provide subject, predicate, and/or object to filter results.",
    args: [
      {
        name: "subject",
        type: "string",
        description: "The subject entity to search for (optional)",
      },
      {
        name: "predicate",
        type: "string",
        description: "The predicate/relationship to search for (optional)",
      },
      {
        name: "object",
        type: "string",
        description: "The object entity to search for (optional)",
      },
    ],
    execute: (input: string): Promise<string> => Effect.runPromise(Effect.gen(function* () {
      const { s, p, o, limit } = parseTriplesInput(input);
      const request: TriplesQueryRequest = {
        limit: limit ?? 20,
        ...(s !== undefined ? { s } : {}),
        ...(p !== undefined ? { p } : {}),
        ...(o !== undefined ? { o } : {}),
        ...(collection !== undefined ? { collection } : {}),
      };
      const res = yield* client.request(request);

      if (res.error !== undefined) return `Error: ${res.error.message}`;

      if (res.triples === undefined || res.triples.length === 0) {
        return "No triples found matching the query.";
      }

      const lines = res.triples.map(
        (t) =>
          `(${termToString(t.s)}) -[${termToString(t.p)}]-> (${termToString(t.o)})`,
      );
      return lines.join("\n");
    })),
  };
}

/**
 * Create an agent tool that delegates to the MCP tool service via NATS.
 *
 * The MCP tool service handles the actual MCP server connection;
 * this function just wraps it as an AgentTool the ReAct agent can invoke.
 */
export function createMcpTool(
  client: EffectRequestResponse<ToolRequest, ToolResponse>,
  toolName: string,
  description: string,
  args: ToolArg[],
): AgentTool {
  return {
    name: toolName,
    description,
    args,
    execute: (input: string): Promise<string> => Effect.runPromise(Effect.gen(function* () {
      const res = yield* client.request({ name: toolName, parameters: input });
      if (res.error !== undefined) return `Error: ${res.error.message}`;
      if (res.text !== undefined) return res.text;
      if (res.object !== undefined) return res.object;
      return "No content";
    })),
  };
}
