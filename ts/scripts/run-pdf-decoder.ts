/**
 * Start the PDF decoder service.
 *
 * Usage: pnpm tsx scripts/run-pdf-decoder.ts
 *
 * Env:
 *   NATS_URL (default: nats://localhost:4222)
 */
import { runMain } from "../packages/flow/src/decoding/pdf-decoder.js";

runMain();
