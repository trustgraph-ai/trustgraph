/**
 * Start the API gateway.
 *
 * Usage: pnpm tsx scripts/run-gateway.ts
 *
 * Env:
 *   NATS_URL     (default: nats://localhost:4222)
 *   GATEWAY_PORT (default: 8088)
 *   GATEWAY_SECRET (optional)
 */
import { run } from "../packages/flow/src/gateway/server.js";

run().catch((err) => {
  console.error("Gateway failed to start:", err);
  process.exit(1);
});
