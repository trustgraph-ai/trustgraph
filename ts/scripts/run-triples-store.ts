import { run } from "../packages/flow/src/storage/triples/falkordb-service.js";

run().catch((err) => {
  console.error("Triples store service failed:", err);
  process.exit(1);
});
