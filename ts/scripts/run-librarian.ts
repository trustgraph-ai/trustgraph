/**
 * Start the librarian service.
 *
 * Usage: pnpm tsx scripts/run-librarian.ts
 *
 * Env:
 *   NATS_URL           (default: nats://localhost:4222)
 *   LIBRARIAN_DATA_DIR (optional, e.g., ./data/librarian)
 */
import { runMain } from "../packages/flow/src/librarian/service.js";

runMain();
