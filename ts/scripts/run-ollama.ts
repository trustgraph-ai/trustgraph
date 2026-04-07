/**
 * Start the Ollama text-completion service.
 *
 * Usage: pnpm tsx scripts/run-ollama.ts
 *
 * Env:
 *   NATS_URL     (default: nats://localhost:4222)
 *   OLLAMA_URL   (default: http://localhost:11434)
 *   OLLAMA_MODEL (default: qwen2.5:0.5b)
 */
import { run } from "../packages/flow/src/model/text-completion/ollama.js";

run().catch((err) => {
  console.error("Ollama LLM service failed:", err);
  process.exit(1);
});
