import { run } from "../packages/flow/src/storage/embeddings/graph-embeddings-service.js";

run().catch((err) => {
  console.error("Graph embeddings store service failed:", err);
  process.exit(1);
});
