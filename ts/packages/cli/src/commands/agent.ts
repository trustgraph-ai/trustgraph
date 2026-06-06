/**
 * Agent CLI commands.
 *
 * Python reference: trustgraph-cli/trustgraph/cli/invoke_agent.py
 */

import { Effect } from "effect";
import * as Argument from "effect/unstable/cli/Argument";
import * as Command from "effect/unstable/cli/Command";
import { cliCommandError, withSocket } from "./util.js";

export const agentCommand = Command.make("agent", {
  question: Argument.string("question").pipe(Argument.withDescription("Question to ask")),
}, ({ question }) =>
  withSocket((socket, opts) =>
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
  ),
).pipe(Command.withDescription("Ask the TrustGraph agent a question"));
