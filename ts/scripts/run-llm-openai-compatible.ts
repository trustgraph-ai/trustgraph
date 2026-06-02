/**
 * Start the OpenAI-compatible text-completion service.
 *
 * Usage: OPENAI_COMPAT_URL=http://localhost:1234/v1 pnpm tsx scripts/run-llm-openai-compatible.ts
 *
 * Env:
 *   NATS_URL            (default: nats://localhost:4222)
 *   OPENAI_COMPAT_URL   (required)
 *   OPENAI_COMPAT_KEY   (default: sk-no-key-required)
 *   OPENAI_COMPAT_MODEL (default: default)
 */
import { runMain } from "../packages/flow/src/model/text-completion/openai-compatible.js";

runMain();
