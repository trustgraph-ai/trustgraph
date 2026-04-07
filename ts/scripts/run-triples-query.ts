import { run } from "../packages/flow/src/query/triples/falkordb-service.js";

run().catch((err) => {
  console.error("Triples query service failed:", err);
  process.exit(1);
});
