/**
 * Start the OpenAI text-completion service.
 *
 * Usage: OPENAI_TOKEN=sk-... pnpm tsx scripts/run-llm-openai.ts
 *
 * Env:
 *   NATS_URL      (default: nats://localhost:4222)
 *   OPENAI_TOKEN  (required)
 *   OPENAI_BASE_URL (optional)
 */
import { run } from "../packages/flow/src/model/text-completion/openai.js";

run().catch((err) => {
  console.error("OpenAI LLM service failed:", err);
  process.exit(1);
});
