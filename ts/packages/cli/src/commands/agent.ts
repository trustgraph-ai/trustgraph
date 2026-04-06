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
        const flow = socket.flow(opts.flow);

        await new Promise<void>((resolve, reject) => {
          flow.agent(
            question,
            (chunk) => {
              // think — show thought process
              if (chunk) process.stderr.write(chunk);
            },
            (chunk) => {
              // observe — show observations
              if (chunk) process.stderr.write(chunk);
            },
            (chunk, complete) => {
              // answer — print to stdout
              if (chunk) process.stdout.write(chunk);
              if (complete) {
                process.stdout.write("\n");
                resolve();
              }
            },
            (err) => reject(new Error(err)),
          );
        });
      } finally {
        socket.close();
      }
    });
}
