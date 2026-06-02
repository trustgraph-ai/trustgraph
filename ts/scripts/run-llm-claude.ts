/**
 * Start the Claude text-completion service.
 *
 * Usage: CLAUDE_KEY=sk-... pnpm tsx scripts/run-llm-claude.ts
 *
 * Env:
 *   NATS_URL   (default: nats://localhost:4222)
 *   CLAUDE_KEY (required)
 */
import { runMain } from "../packages/flow/src/model/text-completion/claude.js";

runMain();
