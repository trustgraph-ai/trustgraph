import { run } from "../packages/flow/src/retrieval/graph-rag-service.js";

run().catch((err) => {
  console.error("Graph RAG service failed:", err);
  process.exit(1);
});
