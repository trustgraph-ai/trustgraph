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
import { runMain } from "../packages/flow/src/model/text-completion/openai.js";

runMain();
