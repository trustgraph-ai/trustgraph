import { run } from "../packages/flow/src/query/embeddings/qdrant-graph-service.js";

run().catch((err) => {
  console.error("Graph embeddings query service failed:", err);
  process.exit(1);
});
