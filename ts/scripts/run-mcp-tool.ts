/**
 * Start the MCP tool service.
 *
 * Usage: pnpm tsx scripts/run-mcp-tool.ts
 *
 * Env:
 *   NATS_URL (default: nats://localhost:4222)
 */
import { runMain } from "../packages/flow/src/agent/mcp-tool/index.js";

runMain();
