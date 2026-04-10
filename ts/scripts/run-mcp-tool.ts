/**
 * Start the MCP tool service.
 *
 * Usage: pnpm tsx scripts/run-mcp-tool.ts
 *
 * Env:
 *   NATS_URL (default: nats://localhost:4222)
 */
import { McpToolService } from "../packages/flow/src/agent/mcp-tool/index.js";

async function run(): Promise<void> {
  await McpToolService.launch("mcp-tool");
}

run().catch((err) => {
  console.error("MCP tool service failed:", err);
  process.exit(1);
});
