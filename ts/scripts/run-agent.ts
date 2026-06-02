/**
 * Start the ReAct agent service.
 *
 * Usage: pnpm tsx scripts/run-agent.ts
 *
 * Env:
 *   NATS_URL (default: nats://localhost:4222)
 */
import {runMain} from "../packages/flow/src/agent/react/service.js";

runMain();
