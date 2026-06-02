/**
 * Start the Azure OpenAI text-completion service.
 *
 * Usage: AZURE_TOKEN=... AZURE_ENDPOINT=... pnpm tsx scripts/run-llm-azure-openai.ts
 *
 * Env:
 *   NATS_URL          (default: nats://localhost:4222)
 *   AZURE_TOKEN       (required)
 *   AZURE_ENDPOINT    (required)
 *   AZURE_MODEL       (default: gpt-4o)
 *   AZURE_API_VERSION (default: 2024-12-01-preview)
 */
import { runMain } from "../packages/flow/src/model/text-completion/azure-openai.js";

runMain();
