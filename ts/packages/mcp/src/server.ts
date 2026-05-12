/**
 * TrustGraph MCP server.
 *
 * Exposes TrustGraph capabilities as MCP tools for AI assistants.
 * Uses the vendored @trustgraph/client for all gateway communication.
 *
 * Python reference: trustgraph-mcp/trustgraph/mcp_server/mcp.py
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { createTrustGraphSocket, type BaseApi, type Term } from "@trustgraph/client";

export function createMcpServer(config: {
  gatewayUrl: string;
  user?: string;
  token?: string;
  flowId?: string;
}) {
  const server = new McpServer({
    name: "trustgraph",
    version: "0.1.0",
  });

  const user = config.user ?? "mcp";
  const socket: BaseApi = createTrustGraphSocket(
    user,
    config.token,
    config.gatewayUrl,
  );

  const flowId = config.flowId ?? "default";

  // ===================== Flow-scoped tools =====================

  // --- Text Completion ---
  server.tool(
    "text_completion",
    "Run a text completion using the configured LLM",
    {
      system: z.string().describe("System prompt"),
      prompt: z.string().describe("User prompt"),
    },
    async ({ system, prompt }) => {
      const flow = socket.flow(flowId);
      const response = await flow.textCompletion(system, prompt);
      return { content: [{ type: "text" as const, text: response }] };
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
      collection: z.string().optional().describe("Collection name"),
    },
    async ({ query, entity_limit, triple_limit, collection }) => {
      const flow = socket.flow(flowId);
      const response = await flow.graphRag(
        query,
        {
          ...(entity_limit !== undefined ? { entityLimit: entity_limit } : {}),
          ...(triple_limit !== undefined ? { tripleLimit: triple_limit } : {}),
        },
        collection,
      );
      return { content: [{ type: "text" as const, text: response }] };
    },
  );

  // --- Document RAG ---
  server.tool(
    "document_rag",
    "Query documents using RAG",
    {
      query: z.string().describe("Natural language query"),
      doc_limit: z.number().optional().describe("Max documents to retrieve"),
      collection: z.string().optional().describe("Collection name"),
    },
    async ({ query, doc_limit, collection }) => {
      const flow = socket.flow(flowId);
      const response = await flow.documentRag(query, doc_limit, collection);
      return { content: [{ type: "text" as const, text: response }] };
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
      const flow = socket.flow(flowId);
      let fullAnswer = "";

      await new Promise<void>((resolve, reject) => {
        flow.agent(
          question,
          () => {}, // think — ignore for MCP
          () => {}, // observe — ignore for MCP
          (chunk, complete) => {
            fullAnswer += chunk;
            if (complete) resolve();
          },
          (err) => reject(new Error(err)),
        );
      });

      return { content: [{ type: "text" as const, text: fullAnswer }] };
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
      const flow = socket.flow(flowId);
      const vectors = await flow.embeddings(text);
      return { content: [{ type: "text" as const, text: JSON.stringify(vectors) }] };
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
      collection: z.string().optional().describe("Collection name"),
    },
    async ({ s, p, o, limit, collection }) => {
      const flow = socket.flow(flowId);
      const sTerm: Term | undefined = s !== undefined && s.length > 0 ? { t: "i", i: s } : undefined;
      const pTerm: Term | undefined = p !== undefined && p.length > 0 ? { t: "i", i: p } : undefined;
      const oTerm: Term | undefined = o !== undefined && o.length > 0 ? { t: "i", i: o } : undefined;
      const triples = await flow.triplesQuery(sTerm, pTerm, oTerm, limit, collection);
      return { content: [{ type: "text" as const, text: JSON.stringify(triples, null, 2) }] };
    },
  );

  // --- Graph Embeddings Query ---
  server.tool(
    "graph_embeddings_query",
    "Find entities similar to a text query using vector embeddings",
    {
      query: z.string().describe("Text to find similar entities for"),
      limit: z.number().optional().describe("Max results"),
      collection: z.string().optional().describe("Collection name"),
    },
    async ({ query, limit, collection }) => {
      const flow = socket.flow(flowId);
      // First embed the query, then search
      const vectors = await flow.embeddings([query]);
      const entities = await flow.graphEmbeddingsQuery(
        vectors[0],
        limit ?? 10,
        collection,
      );
      return { content: [{ type: "text" as const, text: JSON.stringify(entities, null, 2) }] };
    },
  );

  // ===================== Config tools =====================

  server.tool(
    "get_config_all",
    "Get all configuration values",
    {},
    async () => {
      const cfg = socket.config();
      const resp = await cfg.getConfigAll();
      return { content: [{ type: "text" as const, text: JSON.stringify(resp, null, 2) }] };
    },
  );

  server.tool(
    "get_config",
    "Get specific configuration values",
    {
      keys: z.array(
        z.object({
          type: z.string().describe("Config type"),
          key: z.string().describe("Config key"),
        }),
      ).describe("Config keys to retrieve"),
    },
    async ({ keys }) => {
      const cfg = socket.config();
      const resp = await cfg.getConfig(keys);
      return { content: [{ type: "text" as const, text: JSON.stringify(resp, null, 2) }] };
    },
  );

  server.tool(
    "put_config",
    "Set configuration values",
    {
      values: z.array(
        z.object({
          type: z.string().describe("Config type"),
          key: z.string().describe("Config key"),
          value: z.string().describe("Config value (JSON-encoded)"),
        }),
      ).describe("Key-value entries to set"),
    },
    async ({ values }) => {
      const cfg = socket.config();
      const resp = await cfg.putConfig(values);
      return { content: [{ type: "text" as const, text: JSON.stringify(resp) }] };
    },
  );

  server.tool(
    "delete_config",
    "Delete a configuration entry",
    {
      type: z.string().describe("Config type"),
      key: z.string().describe("Config key"),
    },
    async ({ type, key }) => {
      const cfg = socket.config();
      const resp = await cfg.deleteConfig({ type, key });
      return { content: [{ type: "text" as const, text: JSON.stringify(resp) }] };
    },
  );

  // ===================== Flow management tools =====================

  server.tool(
    "get_flows",
    "List all available flows",
    {},
    async () => {
      const flows = socket.flows();
      const ids = await flows.getFlows();
      return { content: [{ type: "text" as const, text: JSON.stringify(ids, null, 2) }] };
    },
  );

  server.tool(
    "get_flow",
    "Get a specific flow definition",
    {
      flow_id: z.string().describe("Flow ID to retrieve"),
    },
    async ({ flow_id }) => {
      const flows = socket.flows();
      const def = await flows.getFlow(flow_id);
      return { content: [{ type: "text" as const, text: JSON.stringify(def, null, 2) }] };
    },
  );

  server.tool(
    "start_flow",
    "Start a flow instance",
    {
      flow_id: z.string().describe("Flow ID"),
      blueprint_name: z.string().describe("Blueprint name"),
      description: z.string().describe("Flow description"),
      parameters: z.record(z.unknown()).optional().describe("Optional flow parameters"),
    },
    async ({ flow_id, blueprint_name, description, parameters }) => {
      const flows = socket.flows();
      const resp = await flows.startFlow(flow_id, blueprint_name, description, parameters);
      return { content: [{ type: "text" as const, text: JSON.stringify(resp, null, 2) }] };
    },
  );

  server.tool(
    "stop_flow",
    "Stop a running flow",
    {
      flow_id: z.string().describe("Flow ID to stop"),
    },
    async ({ flow_id }) => {
      const flows = socket.flows();
      const resp = await flows.stopFlow(flow_id);
      return { content: [{ type: "text" as const, text: JSON.stringify(resp, null, 2) }] };
    },
  );

  // ===================== Library (document) tools =====================

  server.tool(
    "get_documents",
    "List all documents in the library",
    {},
    async () => {
      const lib = socket.librarian();
      const docs = await lib.getDocuments();
      return { content: [{ type: "text" as const, text: JSON.stringify(docs, null, 2) }] };
    },
  );

  server.tool(
    "load_document",
    "Upload a document to the library",
    {
      document: z.string().describe("Base64-encoded document content"),
      mime_type: z.string().describe("Document MIME type"),
      title: z.string().describe("Document title"),
      comments: z.string().optional().describe("Additional comments"),
      tags: z.array(z.string()).optional().describe("Document tags"),
      id: z.string().optional().describe("Optional document ID"),
    },
    async ({ document, mime_type, title, comments, tags, id }) => {
      const lib = socket.librarian();
      const resp = await lib.loadDocument(
        document,
        mime_type,
        title,
        comments ?? "",
        tags ?? [],
        id,
      );
      return { content: [{ type: "text" as const, text: JSON.stringify(resp, null, 2) }] };
    },
  );

  server.tool(
    "remove_document",
    "Remove a document from the library",
    {
      id: z.string().describe("Document ID to remove"),
      collection: z.string().optional().describe("Collection name"),
    },
    async ({ id, collection }) => {
      const lib = socket.librarian();
      const resp = await lib.removeDocument(id, collection);
      return { content: [{ type: "text" as const, text: JSON.stringify(resp) }] };
    },
  );

  // ===================== Prompt tools =====================

  server.tool(
    "get_prompts",
    "List available prompt templates",
    {},
    async () => {
      const cfg = socket.config();
      const prompts = await cfg.getPrompts();
      return { content: [{ type: "text" as const, text: JSON.stringify(prompts, null, 2) }] };
    },
  );

  server.tool(
    "get_prompt",
    "Get a specific prompt template",
    {
      id: z.string().describe("Prompt template ID"),
    },
    async ({ id }) => {
      const cfg = socket.config();
      const prompt = await cfg.getPrompt(id);
      return { content: [{ type: "text" as const, text: JSON.stringify(prompt, null, 2) }] };
    },
  );

  // ===================== Knowledge core tools =====================

  server.tool(
    "get_knowledge_cores",
    "List available knowledge graph cores",
    {},
    async () => {
      const knowledge = socket.knowledge();
      const cores = await knowledge.getKnowledgeCores();
      return { content: [{ type: "text" as const, text: JSON.stringify(cores, null, 2) }] };
    },
  );

  server.tool(
    "delete_kg_core",
    "Delete a knowledge graph core",
    {
      id: z.string().describe("Knowledge core ID"),
      collection: z.string().optional().describe("Collection name"),
    },
    async ({ id, collection }) => {
      const knowledge = socket.knowledge();
      const resp = await knowledge.deleteKgCore(id, collection);
      return { content: [{ type: "text" as const, text: JSON.stringify(resp) }] };
    },
  );

  server.tool(
    "load_kg_core",
    "Load a knowledge graph core",
    {
      id: z.string().describe("Knowledge core ID"),
      flow: z.string().describe("Flow to use for loading"),
      collection: z.string().optional().describe("Collection name"),
    },
    async ({ id, flow, collection }) => {
      const knowledge = socket.knowledge();
      const resp = await knowledge.loadKgCore(id, flow, collection);
      return { content: [{ type: "text" as const, text: JSON.stringify(resp) }] };
    },
  );

  return { server, socket };
}

export async function run(): Promise<void> {
  const { server, socket } = createMcpServer({
    gatewayUrl: process.env.GATEWAY_URL ?? "ws://localhost:8088/api/v1/socket",
    user: process.env.USER_ID ?? "mcp",
    flowId: process.env.FLOW_ID ?? "default",
    ...(process.env.GATEWAY_SECRET !== undefined
      ? { token: process.env.GATEWAY_SECRET }
      : {}),
  });

  const transport = new StdioServerTransport();
  await server.connect(transport);

  process.on("SIGINT", () => {
    socket.close();
    process.exit(0);
  });
}
