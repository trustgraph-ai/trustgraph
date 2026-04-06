/**
 * Start the config service.
 *
 * Usage: pnpm tsx scripts/run-config.ts
 *
 * Env:
 *   NATS_URL           (default: nats://localhost:4222)
 *   CONFIG_PERSIST_PATH (optional, e.g., ./data/config.json)
 */
import { run } from "../packages/flow/src/config/service.js";

run().catch((err) => {
  console.error("Config service failed:", err);
  process.exit(1);
});
