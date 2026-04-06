/**
 * Start the prompt template service.
 *
 * Usage: pnpm tsx scripts/run-prompt.ts
 *
 * Env:
 *   NATS_URL (default: nats://localhost:4222)
 */
import { run } from "../packages/flow/src/prompt/template.js";

run().catch((err) => {
  console.error("Prompt service failed:", err);
  process.exit(1);
});
