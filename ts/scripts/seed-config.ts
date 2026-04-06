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
  });

  // 2. Flow definitions (default flow with all topic mappings)
  console.log("\n── Flow Definitions ──");
  await pushConfig(["flows"], {
    default: {
      topics: {
        // LLM text completion
        "request": "tg.flow.text-completion-request",
        "response": "tg.flow.text-completion-response",
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
        // Triples
        "triples-request": "tg.flow.triples-request",
        "triples-response": "tg.flow.triples-response",
        // Chunking pipeline
        "input": "tg.flow.chunk",
        "output": "tg.flow.chunk",
        "triples": "tg.flow.triples",
        "entity-contexts": "tg.flow.entity-contexts",
      },
    },
  });

  console.log("\nConfiguration seeded successfully.");
}

main().catch((err) => {
  console.error("Seed failed:", err);
  process.exit(1);
});
