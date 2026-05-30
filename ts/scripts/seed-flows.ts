/**
 * Seed flow-manager flow instances for demos.
 *
 * Usage: bun run seed:flows
 * Requires: gateway + flow-manager + config service running
 */

const GATEWAY_URL = process.env.GATEWAY_URL ?? "http://localhost:8088";

const FLOW_TOPICS = {
  // Document processing pipeline
  "decode-input": "tg.flow.document",
  "decode-output": "tg.flow.text-document",
  "decode-triples": "tg.flow.triples",
  "chunk-input": "tg.flow.text-document",
  "chunk-output": "tg.flow.chunk",
  "chunk-triples": "tg.flow.triples",
  "extract-input": "tg.flow.chunk",
  "extract-triples": "tg.flow.triples",
  "extract-entity-contexts": "tg.flow.entity-contexts",
  // Storage consumers
  "store-triples-input": "tg.flow.triples",
  "store-graph-embeddings-input": "tg.flow.entity-contexts",
  // LLM text completion
  "text-completion-request": "tg.flow.text-completion-request",
  "text-completion-response": "tg.flow.text-completion-response",
  // Prompt service
  "prompt-request": "tg.flow.prompt-request",
  "prompt-response": "tg.flow.prompt-response",
  // Graph RAG
  "graph-rag-request": "tg.flow.graph-rag-request",
  "graph-rag-response": "tg.flow.graph-rag-response",
  // Document RAG
  "document-rag-request": "tg.flow.document-rag-request",
  "document-rag-response": "tg.flow.document-rag-response",
  // Triples query
  "triples-request": "tg.flow.triples-request",
  "triples-response": "tg.flow.triples-response",
  // Agent
  "agent-request": "tg.flow.agent-request",
  "agent-response": "tg.flow.agent-response",
  // Embeddings
  "embeddings-request": "tg.flow.embeddings-request",
  "embeddings-response": "tg.flow.embeddings-response",
  // Graph embeddings query
  "graph-embeddings-request": "tg.flow.graph-embeddings-request",
  "graph-embeddings-response": "tg.flow.graph-embeddings-response",
  // Document embeddings query
  "document-embeddings-request": "tg.flow.document-embeddings-request",
  "document-embeddings-response": "tg.flow.document-embeddings-response",
  // Librarian RPC (for PDF decoder)
  "librarian-request": "tg.flow.librarian-request",
  "librarian-response": "tg.flow.librarian-response",
  // MCP tool invocation
  "mcp-tool-request": "tg.flow.mcp-tool-request",
  "mcp-tool-response": "tg.flow.mcp-tool-response",
} as const;

const SEEDED_FLOWS = [
  {
    id: "default",
    description: "Full-stack default pipeline for ingestion, RAG, and agent demos.",
  },
  {
    id: "beep-hole",
    description: "Workbench sandbox flow for ad hoc experiments.",
  },
  {
    id: "ai-graph-demo",
    description: "Graph RAG over the seeded AI industry knowledge graph.",
  },
  {
    id: "doc-rag-demo",
    description: "Document RAG over the seeded demo document chunks.",
  },
  {
    id: "agent-demo",
    description: "Agent flow wired to seeded knowledge and document tools.",
  },
] as const;

async function postJson<T>(path: string, body: Record<string, unknown>): Promise<T> {
  const res = await fetch(`${GATEWAY_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json() as T & { error?: { message?: string } };
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}: ${JSON.stringify(data)}`);
  }
  if (data.error !== undefined) {
    throw new Error(data.error.message ?? JSON.stringify(data.error));
  }
  return data;
}

async function listFlows(): Promise<Set<string>> {
  const response = await postJson<{ "flow-ids"?: string[] }>("/api/v1/flow", {
    operation: "list-flows",
  });
  return new Set(response["flow-ids"] ?? []);
}

async function startMissingFlows(existing: Set<string>): Promise<void> {
  for (const flow of SEEDED_FLOWS) {
    if (existing.has(flow.id)) {
      console.log(`  Flow ${flow.id}: already running`);
      continue;
    }

    await postJson("/api/v1/flow", {
      operation: "start-flow",
      "flow-id": flow.id,
      "blueprint-name": "default",
      description: flow.description,
      parameters: {
        user: "default",
        collection: "default",
      },
    });
    existing.add(flow.id);
    console.log(`  Flow ${flow.id}: started`);
  }
}

async function ensureFlowConfig(): Promise<void> {
  const values = Object.fromEntries(
    SEEDED_FLOWS.map((flow) => [flow.id, { topics: FLOW_TOPICS }]),
  );

  const response = await postJson<{ version?: number }>("/api/v1/config", {
    operation: "put",
    keys: ["flows"],
    values,
  });
  console.log(`  Flow config topics pushed -> version ${response.version ?? "unknown"}`);
}

async function main(): Promise<void> {
  console.log("Seeding TrustGraph flows...\n");

  const existing = await listFlows();
  await startMissingFlows(existing);

  console.log("\nAligning flow config topics...");
  await ensureFlowConfig();

  const finalFlows = [...(await listFlows())].sort();
  console.log(`\nActive flows: ${finalFlows.join(", ")}`);
  console.log("\nFlow seeding complete.");
}

main().catch((err) => {
  console.error("Seed flows failed:", err);
  process.exit(1);
});
