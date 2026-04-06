/**
 * Graph RAG CLI commands.
 *
 * Python reference: trustgraph-cli/trustgraph/cli/invoke_graph_rag.py
 */

import type { Command } from "commander";
import { createSocket, getOpts } from "./util.js";

export function registerGraphRagCommands(program: Command): void {
  program
    .command("graph-rag")
    .description("Query the knowledge graph using RAG")
    .argument("<query>", "Natural language query")
    .option("--entity-limit <n>", "Max entities", "50")
    .option("--triple-limit <n>", "Max triples per entity", "30")
    .action(async (query: string, cmdOpts, cmd) => {
      const opts = getOpts(cmd);
      const socket = await createSocket(opts);

      try {
        const resp = await socket.request(
          "graph-rag",
          {
            query,
            entity_limit: parseInt(cmdOpts.entityLimit, 10),
            triple_limit: parseInt(cmdOpts.tripleLimit, 10),
          },
          { flowId: opts.flow },
        ) as { response?: string };

        console.log(resp.response ?? JSON.stringify(resp, null, 2));
      } finally {
        await socket.close();
      }
    });

  program
    .command("document-rag")
    .description("Query documents using RAG")
    .argument("<query>", "Natural language query")
    .action(async (query: string, _cmdOpts, cmd) => {
      const opts = getOpts(cmd);
      const socket = await createSocket(opts);

      try {
        const resp = await socket.request(
          "document-rag",
          { query },
          { flowId: opts.flow },
        ) as { response?: string };

        console.log(resp.response ?? JSON.stringify(resp, null, 2));
      } finally {
        await socket.close();
      }
    });
}
