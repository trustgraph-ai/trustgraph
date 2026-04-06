/**
 * Agent CLI commands.
 *
 * Python reference: trustgraph-cli/trustgraph/cli/invoke_agent.py
 */

import type { Command } from "commander";
import { createSocket, getOpts } from "./util.js";

export function registerAgentCommands(program: Command): void {
  program
    .command("agent")
    .description("Ask the TrustGraph agent a question")
    .argument("<question>", "Question to ask")
    .action(async (question: string, _opts, cmd) => {
      const opts = getOpts(cmd);
      const socket = await createSocket(opts);

      try {
        const resp = await socket.request("agent", { question }, {
          flowId: opts.flow,
          onChunk: (chunk) => {
            const c = chunk as { answer?: string };
            if (c.answer) process.stdout.write(c.answer);
          },
        });

        const r = resp as { answer?: string };
        if (r.answer) console.log(r.answer);
      } finally {
        await socket.close();
      }
    });
}
