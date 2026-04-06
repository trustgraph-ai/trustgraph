/**
 * Start the knowledge core service.
 *
 * Usage: pnpm tsx scripts/run-knowledge.ts
 *
 * Env:
 *   NATS_URL            (default: nats://localhost:4222)
 *   KNOWLEDGE_DATA_DIR  (optional, e.g., ./data/knowledge)
 */
import { run } from "../packages/flow/src/cores/service.js";

run().catch((err) => {
  console.error("Knowledge core service failed:", err);
  process.exit(1);
});
