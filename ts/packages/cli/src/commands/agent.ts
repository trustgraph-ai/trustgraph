/**
 * Agent CLI commands.
 *
 * Python reference: trustgraph-cli/trustgraph/cli/invoke_agent.py
 */

import type { Command } from "commander";
import { Effect } from "effect";
import { cliCommandError, withSocket } from "./util.js";

export function registerAgentCommands(program: Command): void {
  program
    .command("agent")
    .description("Ask the TrustGraph agent a question")
    .argument("<question>", "Question to ask")
    .action((question: string, _opts, cmd) =>
      Effect.runPromise(withSocket(cmd, (socket, opts) =>
        Effect.gen(function* () {
        const flow = socket.flow(opts.flow);

          yield* Effect.callback<void, ReturnType<typeof cliCommandError>>((resume) => {
          flow.agent(
            question,
            (chunk) => {
              // think — show thought process
              if (chunk.length > 0) process.stderr.write(chunk);
            },
            (chunk) => {
              // observe — show observations
              if (chunk.length > 0) process.stderr.write(chunk);
            },
            (chunk, complete) => {
              // answer — print to stdout
              if (chunk.length > 0) process.stdout.write(chunk);
              if (complete) {
                process.stdout.write("\n");
                  resume(Effect.void);
              }
            },
              (err) => resume(Effect.fail(cliCommandError("agent", err))),
          );
        });
        }),
      )),
    );
}
