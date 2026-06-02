/**
 * Start the Mistral text-completion service.
 *
 * Usage: MISTRAL_TOKEN=... pnpm tsx scripts/run-llm-mistral.ts
 *
 * Env:
 *   NATS_URL      (default: nats://localhost:4222)
 *   MISTRAL_TOKEN (required)
 *   MISTRAL_MODEL (default: ministral-8b-latest)
 */
import { runMain } from "../packages/flow/src/model/text-completion/mistral.js";

runMain();
