/**
 * Start the flow manager service.
 *
 * Usage: pnpm tsx scripts/run-flow-manager.ts
 *
 * Env:
 *   NATS_URL (default: nats://localhost:4222)
 */
import { run } from "../packages/flow/src/flow-manager/service.js";

run().catch((err) => {
  console.error("Flow manager failed:", err);
  process.exit(1);
});
