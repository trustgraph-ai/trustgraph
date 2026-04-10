/**
 * MVP tools for the ReAct agent.
 *
 * Each tool wraps a RequestResponse client from the flow, providing the agent
 * with access to existing TrustGraph retrieval services.
 */

import type {
  RequestResponse,
  GraphRagRequest,
  GraphRagResponse,
  DocumentRagRequest,
  DocumentRagResponse,
  TriplesQueryRequest,
  TriplesQueryResponse,
  ToolRequest,
  ToolResponse,
  Term,
} from "@trustgraph/base";

import type { AgentTool, ToolArg } from "./types.js";

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
  try {
    const parsed = JSON.parse(input) as Record<string, unknown>;
    if (typeof parsed === "object" && parsed !== null && "question" in parsed) {
      return String(parsed.question);
    }
    // If it's a string JSON value, use it directly
    if (typeof parsed === "string") {
      return parsed;
    }
  } catch {
    // Not valid JSON -- treat as plain text
  }
  return input;
}

/**
 * Query the knowledge graph for information about entities and their relationships.
 */
export function createKnowledgeQueryTool(
  client: RequestResponse<GraphRagRequest, GraphRagResponse>,
  collection?: string,
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
    async execute(input: string): Promise<string> {
      const question = parseQuestion(input);
      const res = await client.request({ query: question, collection });
      if (res.error) return `Error: ${res.error.message}`;
      return res.response;
    },
  };
}

/**
 * Search documents for relevant information.
 */
export function createDocumentQueryTool(
  client: RequestResponse<DocumentRagRequest, DocumentRagResponse>,
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
    async execute(input: string): Promise<string> {
      const question = parseQuestion(input);
      const res = await client.request({ query: question, collection });
      if (res.error) return `Error: ${res.error.message}`;
      return res.response;
    },
  };
}

/**
 * Parse triples query input. Accepts JSON with optional s, p, o fields.
 */
function parseTriplesInput(input: string): {
  s?: Term;
  p?: Term;
  o?: Term;
  limit?: number;
} {
  try {
    const parsed = JSON.parse(input) as Record<string, unknown>;

    const toTerm = (val: unknown): Term | undefined => {
      if (typeof val === "string") {
        return { type: "LITERAL", value: val };
      }
      if (typeof val === "object" && val !== null && "type" in val) {
        return val as Term;
      }
      return undefined;
    };

    return {
      s: toTerm(parsed.subject ?? parsed.s),
      p: toTerm(parsed.predicate ?? parsed.p),
      o: toTerm(parsed.object ?? parsed.o),
      limit:
        typeof parsed.limit === "number" ? parsed.limit : undefined,
    };
  } catch {
    // If not valid JSON, treat as a subject search
    return {
      s: { type: "LITERAL", value: input },
    };
  }
}

/**
 * Query for specific triples (subject-predicate-object relationships) in the knowledge graph.
 */
export function createTriplesQueryTool(
  client: RequestResponse<TriplesQueryRequest, TriplesQueryResponse>,
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
    async execute(input: string): Promise<string> {
      const { s, p, o, limit } = parseTriplesInput(input);
      const res = await client.request({
        s,
        p,
        o,
        collection,
        limit: limit ?? 20,
      });

      if (res.error) return `Error: ${res.error.message}`;

      if (!res.triples || res.triples.length === 0) {
        return "No triples found matching the query.";
      }

      const lines = res.triples.map(
        (t) =>
          `(${termToString(t.s)}) -[${termToString(t.p)}]-> (${termToString(t.o)})`,
      );
      return lines.join("\n");
    },
  };
}

/**
 * Create an agent tool that delegates to the MCP tool service via NATS.
 *
 * The MCP tool service handles the actual MCP server connection;
 * this function just wraps it as an AgentTool the ReAct agent can invoke.
 */
export function createMcpTool(
  client: RequestResponse<ToolRequest, ToolResponse>,
  toolName: string,
  description: string,
  args: ToolArg[],
): AgentTool {
  return {
    name: toolName,
    description,
    args,
    async execute(input: string): Promise<string> {
      const res = await client.request({ name: toolName, parameters: input });
      if (res.error) return `Error: ${res.error.message}`;
      if (res.text) return res.text;
      if (res.object) return res.object;
      return "No content";
    },
  };
}
