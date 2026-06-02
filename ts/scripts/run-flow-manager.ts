/**
 * Start the flow manager service.
 *
 * Usage: pnpm tsx scripts/run-flow-manager.ts
 *
 * Env:
 *   NATS_URL (default: nats://localhost:4222)
 */
import { runMain } from "../packages/flow/src/flow-manager/service.js";

runMain();
