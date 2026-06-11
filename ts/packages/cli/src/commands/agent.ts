/**
 * Agent CLI commands.
 *
 * Python reference: trustgraph-cli/trustgraph/cli/invoke_agent.py
 */

import { Effect } from "effect";
import * as Argument from "effect/unstable/cli/Argument";
import * as Command from "effect/unstable/cli/Command";
import type { CliCommandError } from "./util.js";
import { cliCommandError, withGatewayClient, } from "./util.js";

function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? value as Record<string, unknown>
    : {};
}

function stringProperty(source: unknown, key: string): string | undefined {
  const value = asRecord(source)[key];
  return typeof value === "string" ? value : undefined;
}

function booleanProperty(source: unknown, key: string): boolean | undefined {
  const value = asRecord(source)[key];
  return typeof value === "boolean" ? value : undefined;
}

function responseErrorMessage(source: unknown): string | undefined {
  const error = asRecord(source).error;
  if (typeof error === "string") return error;
  return stringProperty(error, "message");
}

export const agentCommand = Command.make("agent", {
  question: Argument.string("question").pipe(Argument.withDescription("Question to ask")),
}, ({ question }) =>
  withGatewayClient((client, opts) =>
    Effect.gen(function* () {
      let streamError: CliCommandError | undefined;

      yield* client.runDispatchStream(
        {
          scope: "flow",
          flow: opts.flow,
          service: "agent",
          request: {
            question,
            user: opts.user,
            collection: "default",
            streaming: true,
          },
        },
        (chunk) => {
          const resp = asRecord(chunk.response);
          const chunkType = stringProperty(resp, "chunk_type");
          const error = chunkType === "error" ? responseErrorMessage(resp) ?? "Unknown agent error" : responseErrorMessage(resp);
          if (error !== undefined) {
            streamError = cliCommandError("agent", error);
            return true;
          }

          const content = stringProperty(resp, "content") ?? "";
          const messageComplete = booleanProperty(resp, "end_of_message") === true;
          const dialogComplete = chunk.complete === true || booleanProperty(resp, "end_of_dialog") === true;

          if (chunkType === "thought" || chunkType === "observation") {
            if (content.length > 0) process.stderr.write(content);
          } else if (chunkType === "answer" || chunkType === "final-answer") {
            if (content.length > 0) process.stdout.write(content);
            if (messageComplete || dialogComplete) process.stdout.write("\n");
          }

          return dialogComplete;
        },
        { timeoutMs: 120_000, retries: 2 },
      );

      if (streamError !== undefined) {
        return yield* streamError;
      }
    }),
  ),
).pipe(Command.withDescription("Ask the TrustGraph agent a question"));
