/**
 * TrustGraph MCP server.
 *
 * Exposes TrustGraph capabilities as MCP tools for AI assistants.
 * Communicates with the TrustGraph gateway via WebSocket.
 *
 * Python reference: trustgraph-mcp/trustgraph/mcp_server/mcp.py
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { SocketManager } from "./socket-manager.js";

export function createMcpServer(config: {
  gatewayUrl: string;
  token?: string;
  flowId?: string;
}) {
  const server = new McpServer({
    name: "trustgraph",
    version: "0.1.0",
  });

  const socket = new SocketManager({
    gatewayUrl: config.gatewayUrl,
    token: config.token,
  });

  const flowId = config.flowId ?? "default";

  // --- Text Completion ---
  server.tool(
    "text_completion",
    "Run a text completion using the configured LLM",
    {
      system: z.string().describe("System prompt"),
      prompt: z.string().describe("User prompt"),
    },
    async ({ system, prompt }) => {
      const resp = await socket.request("text-completion", { system, prompt }, { flowId }) as Record<string, unknown>;
      return { content: [{ type: "text" as const, text: String(resp.response ?? resp) }] };
    },
  );

  // --- Graph RAG ---
  server.tool(
    "graph_rag",
    "Query the knowledge graph using RAG",
    {
      query: z.string().describe("Natural language query"),
      entity_limit: z.number().optional().describe("Max entities to retrieve"),
      triple_limit: z.number().optional().describe("Max triples per entity"),
    },
    async ({ query, entity_limit, triple_limit }) => {
      const resp = await socket.request(
        "graph-rag",
        { query, entity_limit, triple_limit },
        { flowId },
      ) as Record<string, unknown>;
      return { content: [{ type: "text" as const, text: String(resp.response ?? resp) }] };
    },
  );

  // --- Agent ---
  server.tool(
    "agent",
    "Ask the TrustGraph agent a question",
    {
      question: z.string().describe("Question for the agent"),
    },
    async ({ question }) => {
      const resp = await socket.request("agent", { question }, { flowId }) as Record<string, unknown>;
      return { content: [{ type: "text" as const, text: String(resp.answer ?? resp) }] };
    },
  );

  // --- Embeddings ---
  server.tool(
    "embeddings",
    "Generate text embeddings",
    {
      text: z.array(z.string()).describe("Texts to embed"),
    },
    async ({ text }) => {
      const resp = await socket.request("embeddings", { text }, { flowId }) as Record<string, unknown>;
      return { content: [{ type: "text" as const, text: JSON.stringify(resp) }] };
    },
  );

  // --- Triples Query ---
  server.tool(
    "triples_query",
    "Query the knowledge graph for triples matching a pattern",
    {
      s: z.string().optional().describe("Subject IRI"),
      p: z.string().optional().describe("Predicate IRI"),
      o: z.string().optional().describe("Object IRI or literal"),
      limit: z.number().optional().describe("Max results"),
    },
    async ({ s, p, o, limit }) => {
      const request: Record<string, unknown> = { limit };
      if (s) request.s = { type: "IRI", iri: s };
      if (p) request.p = { type: "IRI", iri: p };
      if (o) request.o = { type: "IRI", iri: o };

      const resp = await socket.request("triples-query", request, { flowId }) as Record<string, unknown>;
      return { content: [{ type: "text" as const, text: JSON.stringify(resp, null, 2) }] };
    },
  );

  // --- Graph Embeddings Query ---
  server.tool(
    "graph_embeddings_query",
    "Find entities similar to a text query using vector embeddings",
    {
      query: z.string().describe("Text to find similar entities for"),
      limit: z.number().optional().describe("Max results"),
    },
    async ({ query, limit }) => {
      // First embed the query, then search
      const embResp = await socket.request("embeddings", { text: [query] }, { flowId }) as { vectors: number[][] };
      const resp = await socket.request(
        "graph-embeddings-query",
        { vectors: embResp.vectors, limit: limit ?? 10 },
        { flowId },
      ) as Record<string, unknown>;
      return { content: [{ type: "text" as const, text: JSON.stringify(resp, null, 2) }] };
    },
  );

  // --- Config ---
  server.tool(
    "get_config",
    "Get configuration values",
    {
      keys: z.array(z.string()).describe("Config keys to retrieve"),
    },
    async ({ keys }) => {
      const resp = await socket.request("config", { operation: "get", keys }) as Record<string, unknown>;
      return { content: [{ type: "text" as const, text: JSON.stringify(resp, null, 2) }] };
    },
  );

  server.tool(
    "put_config",
    "Set configuration values",
    {
      values: z.record(z.unknown()).describe("Key-value pairs to set"),
    },
    async ({ values }) => {
      const resp = await socket.request("config", { operation: "put", values }) as Record<string, unknown>;
      return { content: [{ type: "text" as const, text: JSON.stringify(resp) }] };
    },
  );

  return { server, socket };
}

export async function run(): Promise<void> {
  const { server, socket } = createMcpServer({
    gatewayUrl: process.env.GATEWAY_URL ?? "ws://localhost:8088/api/v1/socket",
    token: process.env.GATEWAY_SECRET,
    flowId: process.env.FLOW_ID ?? "default",
  });

  const transport = new StdioServerTransport();
  await server.connect(transport);

  process.on("SIGINT", async () => {
    await socket.close();
    process.exit(0);
  });
}
