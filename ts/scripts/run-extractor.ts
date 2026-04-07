import { run } from "../packages/flow/src/extract/knowledge-extract.js";

run().catch((err) => {
  console.error("Knowledge extract service failed:", err);
  process.exit(1);
});
