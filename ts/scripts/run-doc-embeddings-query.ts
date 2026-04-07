import { run } from "../packages/flow/src/query/embeddings/qdrant-doc-service.js";

run().catch((err) => {
  console.error("Document embeddings query service failed:", err);
  process.exit(1);
});
