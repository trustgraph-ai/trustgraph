/**
 * Start the prompt template service.
 *
 * Usage: pnpm tsx scripts/run-prompt.ts
 *
 * Env:
 *   NATS_URL (default: nats://localhost:4222)
 */
import { runMain } from "../packages/flow/src/prompt/template.js";

runMain();
