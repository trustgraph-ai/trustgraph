/**
 * Start the config service.
 *
 * Usage: pnpm tsx scripts/run-config.ts
 *
 * Env:
 *   NATS_URL           (default: nats://localhost:4222)
 *   CONFIG_PERSIST_PATH (optional, e.g., ./data/config.json)
 */
import {runMain} from "../packages/flow/src/config/service.js";

runMain();
