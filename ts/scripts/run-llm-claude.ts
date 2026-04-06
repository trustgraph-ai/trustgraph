/**
 * Start the Claude text-completion service.
 *
 * Usage: CLAUDE_KEY=sk-... pnpm tsx scripts/run-llm-claude.ts
 *
 * Env:
 *   NATS_URL   (default: nats://localhost:4222)
 *   CLAUDE_KEY (required)
 */
import { run } from "../packages/flow/src/model/text-completion/claude.js";

run().catch((err) => {
  console.error("Claude LLM service failed:", err);
  process.exit(1);
});
