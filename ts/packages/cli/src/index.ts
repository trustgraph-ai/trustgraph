#!/usr/bin/env node

/**
 * Unified TrustGraph CLI.
 *
 * Replaces the 60+ individual Python CLI scripts with a single
 * `tg` command using subcommands.
 *
 * Python reference: trustgraph-cli/trustgraph/cli/
 */

import { Command } from "commander";
import { registerAgentCommands } from "./commands/agent.js";
import { registerGraphRagCommands } from "./commands/graph-rag.js";
import { registerConfigCommands } from "./commands/config.js";
import { registerFlowCommands } from "./commands/flow.js";
import { registerLibraryCommands } from "./commands/library.js";
import { registerTriplesCommands } from "./commands/triples.js";
import { registerEmbeddingsCommands } from "./commands/embeddings.js";

const program = new Command();

program
  .name("tg")
  .description("TrustGraph CLI — interact with TrustGraph services")
  .version("0.1.0")
  .option("-g, --gateway <url>", "Gateway WebSocket URL", "ws://localhost:8088/api/v1/socket")
  .option("-u, --user <id>", "User identifier", "cli")
  .option("-t, --token <token>", "Authentication token")
  .option("-f, --flow <id>", "Flow ID", "default");

registerAgentCommands(program);
registerGraphRagCommands(program);
registerConfigCommands(program);
registerFlowCommands(program);
registerLibraryCommands(program);
registerTriplesCommands(program);
registerEmbeddingsCommands(program);

program.parse();
