import { run } from "../packages/flow/src/embeddings/ollama.js";

run().catch((err) => {
  console.error("Embeddings service failed:", err);
  process.exit(1);
});
