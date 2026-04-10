/**
 * Seed configuration — pushes prompt templates and flow definitions
 * needed for the full processing pipeline.
 *
 * Usage: pnpm seed
 * Requires: gateway + config service running
 */

const GATEWAY_URL = process.env.GATEWAY_URL ?? "http://localhost:8088";

async function pushConfig(keys: string[], values: Record<string, unknown>): Promise<void> {
  const res = await fetch(`${GATEWAY_URL}/api/v1/config`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ operation: "put", keys, values }),
  });
  const data = await res.json();
  if (data.error) throw new Error(`Config push failed: ${data.error.message}`);
  console.log(`  Pushed config [${keys.join("/")}] → version ${data.version}`);
}

async function main(): Promise<void> {
  console.log("Seeding TrustGraph configuration...\n");

  // 1. Prompt templates
  console.log("── Prompt Templates ──");
  await pushConfig(["prompt"], {
    "extract-relationships": {
      system: "You are a helpful assistant that extracts structured knowledge from text.",
      prompt: [
        "Study the following text and derive entity relationships.",
        "For each relationship, derive the subject, predicate and object.",
        "",
        "Output as a JSON array of objects with keys:",
        "- subject: the subject of the relationship",
        "- predicate: the predicate",
        "- object: the object of the relationship",
        "",
        "Here is the text:",
        "{text}",
        "",
        "Requirements:",
        "- Respond only with a valid JSON array.",
        "- Do not include explanations or markdown formatting.",
        "- Example: [{\"subject\": \"Earth\", \"predicate\": \"orbits\", \"object\": \"Sun\"}]",
      ].join("\n"),
    },
    "extract-definitions": {
      system: "You are a helpful assistant that extracts entity definitions from text.",
      prompt: [
        "Study the following text and derive definitions for any discovered entities.",
        "Do not provide definitions for entities whose definitions are incomplete or unknown.",
        "",
        "Output as a JSON array of objects with keys:",
        "- entity: the name of the entity",
        "- definition: English text which defines the entity",
        "",
        "Here is the text:",
        "{text}",
        "",
        "Requirements:",
        "- Respond only with a valid JSON array.",
        "- Do not include explanations or markdown formatting.",
        "- Do not include null or unknown definitions.",
        "- Example: [{\"entity\": \"photosynthesis\", \"definition\": \"The process by which plants convert sunlight into energy\"}]",
      ].join("\n"),
    },
    "document-prompt": {
      system: "You are a helpful assistant. Use only the provided context to answer questions.",
      prompt: [
        "Use the following context to answer the question.",
        "Do not speculate if the answer is not found in the context.",
        "",
        "Context:",
        "{documents}",
        "",
        "Question: {query}",
      ].join("\n"),
    },
    "kg-prompt": {
      system: "You are a helpful assistant that answers questions using knowledge graph data.",
      prompt: [
        "Use the following knowledge graph information to answer the question.",
        "",
        "Knowledge:",
        "{knowledge}",
        "",
        "Question: {query}",
      ].join("\n"),
    },
    "extract-concepts": {
      system: "You extract key concepts and entities from questions.",
      prompt: [
        "Extract the key concepts and entities from the following question.",
        "Return one concept per line, no numbering or bullets.",
        "",
        "Question: {query}",
      ].join("\n"),
    },
    "kg-edge-scoring": {
      system: "You are a knowledge graph expert that scores the relevance of graph edges to a query.",
      prompt: [
        "Given the following question and a list of knowledge graph edges,",
        "score each edge for relevance to answering the question.",
        "Return a JSON array of objects with 'id' and 'score' (0.0 to 1.0).",
        "",
        "Question: {query}",
        "",
        "Edges:",
        "{knowledge}",
        "",
        "Requirements:",
        "- Respond only with a valid JSON array.",
        "- Example: [{\"id\": \"0\", \"score\": 0.9}, {\"id\": \"1\", \"score\": 0.2}]",
      ].join("\n"),
    },
    "graph-rag-synthesize": {
      system: "You are a helpful assistant that answers questions using knowledge graph data. Only use the provided context.",
      prompt: [
        "Use the following knowledge graph relationships to answer the question.",
        "Do not speculate if the answer is not found in the context.",
        "",
        "Knowledge:",
        "{context}",
        "",
        "Question: {query}",
      ].join("\n"),
    },
    "document-rag-synthesize": {
      system: "You are a helpful assistant. Use only the provided document context to answer questions.",
      prompt: [
        "Use the following document excerpts to answer the question.",
        "Do not speculate if the answer is not found in the context.",
        "",
        "Documents:",
        "{context}",
        "",
        "Question: {query}",
      ].join("\n"),
    },
  });

  // 2. Flow definitions (default flow with all topic mappings)
  console.log("\n── Flow Definitions ──");
  await pushConfig(["flows"], {
    default: {
      topics: {
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
      },
    },
  });

  // 3. MCP server configuration (external tool providers)
  console.log("\n── MCP Configuration ──");
  const braveApiKey = process.env.BRAVE_API_KEY;
  if (braveApiKey) {
    await pushConfig(["mcp"], {
      "brave-search": JSON.stringify({
        url: "http://localhost:8383/mcp",
        "remote-name": "brave_web_search",
      }),
    });
    console.log("  Brave Search MCP service configured");
  } else {
    console.log("  Skipping MCP config (no BRAVE_API_KEY set)");
  }

  // 4. Agent tool configuration (maps tools to implementations)
  console.log("\n── Tool Configuration ──");
  const toolConfig: Record<string, string> = {
    "knowledge-query": JSON.stringify({
      type: "knowledge-query",
      name: "KnowledgeQuery",
      description: "Query the knowledge graph for information about entities and their relationships.",
      group: ["default"],
    }),
    "document-query": JSON.stringify({
      type: "document-query",
      name: "DocumentQuery",
      description: "Search the document library for relevant information using semantic search.",
      group: ["default"],
    }),
    "triples-query": JSON.stringify({
      type: "triples-query",
      name: "TriplesQuery",
      description: "Query for specific triples (subject-predicate-object relationships) in the knowledge graph.",
      group: ["default"],
    }),
  };

  // Add Brave Search tool if API key is available
  if (braveApiKey) {
    toolConfig["brave-search"] = JSON.stringify({
      type: "mcp-tool",
      name: "brave-search",
      description: "Search the web using Brave Search. Returns web search results including titles, URLs, and descriptions.",
      "mcp-tool": "brave-search",
      group: ["default"],
      arguments: [
        { name: "query", type: "string", description: "The search query" },
      ],
    });
    console.log("  Brave Search tool added");
  }

  await pushConfig(["tool"], toolConfig);

  console.log("\nConfiguration seeded successfully.");
}

main().catch((err) => {
  console.error("Seed failed:", err);
  process.exit(1);
});
