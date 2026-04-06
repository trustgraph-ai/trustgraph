/**
 * Start the ReAct agent service.
 *
 * Usage: pnpm tsx scripts/run-agent.ts
 *
 * Env:
 *   NATS_URL (default: nats://localhost:4222)
 */
import { run } from "../packages/flow/src/agent/react/service.js";

run().catch((err) => {
  console.error("Agent service failed:", err);
  process.exit(1);
});
