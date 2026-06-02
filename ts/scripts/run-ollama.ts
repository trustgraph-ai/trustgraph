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
import { runMain } from "../packages/flow/src/model/text-completion/ollama.js";

runMain();
