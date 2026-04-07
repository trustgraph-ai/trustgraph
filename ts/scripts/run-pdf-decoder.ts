/**
 * Start the PDF decoder service.
 *
 * Usage: pnpm tsx scripts/run-pdf-decoder.ts
 *
 * Env:
 *   NATS_URL (default: nats://localhost:4222)
 */
import { run } from "../packages/flow/src/decoding/pdf-decoder.js";

run().catch((err) => {
  console.error("PDF decoder service failed:", err);
  process.exit(1);
});
