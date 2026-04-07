import { run } from "../packages/flow/src/retrieval/document-rag-service.js";

run().catch((err) => {
  console.error("Document RAG service failed:", err);
  process.exit(1);
});
