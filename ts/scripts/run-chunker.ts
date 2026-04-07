import { run } from "../packages/flow/src/chunking/service.js";

run().catch((err) => {
  console.error("Chunking service failed:", err);
  process.exit(1);
});
