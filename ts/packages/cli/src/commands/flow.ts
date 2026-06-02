/**
 * Flow management CLI commands.
 *
 * Python reference: trustgraph-cli/trustgraph/cli/start_flow.py, stop_flow.py, etc.
 */

import type { Command } from "commander";
import { Effect } from "effect";
import * as S from "effect/Schema";
import { cliCommandError, withSocket, writeJson } from "./util.js";

export function registerFlowCommands(program: Command): void {
  const flow = program
    .command("flow")
    .description("Flow management");

  flow
    .command("list")
    .description("List active flows")
    .action((_opts, cmd) =>
      Effect.runPromise(withSocket(cmd, (socket) =>
        Effect.gen(function* () {
        const flows = socket.flows();
          const ids = yield* Effect.tryPromise({
            try: () => flows.getFlows(),
            catch: (error) => cliCommandError("flow.list", error),
          });
          yield* writeJson(ids);
        }),
      )),
    );

  flow
    .command("get")
    .description("Get a flow definition")
    .argument("<id>", "Flow ID")
    .action((id: string, _opts, cmd) =>
      Effect.runPromise(withSocket(cmd, (socket) =>
        Effect.gen(function* () {
        const flows = socket.flows();
          const def = yield* Effect.tryPromise({
            try: () => flows.getFlow(id),
            catch: (error) => cliCommandError("flow.get", error),
          });
          yield* writeJson(def);
        }),
      )),
    );

  flow
    .command("start")
    .description("Start a flow")
    .argument("<id>", "Flow ID")
    .requiredOption("-b, --blueprint <name>", "Blueprint name")
    .option("-d, --description <text>", "Flow description", "")
    .option("-p, --parameters <json>", "Parameters as JSON")
    .action((id: string, cmdOpts, cmd) =>
      Effect.runPromise(withSocket(cmd, (socket) =>
        Effect.gen(function* () {
        const flows = socket.flows();
        const rawParameters = cmdOpts.parameters as string | undefined;
        const params = rawParameters !== undefined && rawParameters.length > 0
          ? yield* S.decodeUnknownEffect(S.UnknownFromJsonString)(rawParameters).pipe(
              Effect.flatMap(S.decodeUnknownEffect(S.Record(S.String, S.Unknown))),
              Effect.mapError((error) => cliCommandError("flow.start.parameters", error)),
            )
          : undefined;
          const resp = yield* Effect.tryPromise({
            try: () =>
              flows.startFlow(
                id,
                cmdOpts.blueprint as string,
                cmdOpts.description as string,
                params,
              ),
            catch: (error) => cliCommandError("flow.start", error),
          });
          yield* writeJson(resp);
        }),
      )),
    );

  flow
    .command("stop")
    .description("Stop a flow")
    .argument("<id>", "Flow ID")
    .action((id: string, _opts, cmd) =>
      Effect.runPromise(withSocket(cmd, (socket) =>
        Effect.gen(function* () {
        const flows = socket.flows();
          const resp = yield* Effect.tryPromise({
            try: () => flows.stopFlow(id),
            catch: (error) => cliCommandError("flow.stop", error),
          });
          yield* writeJson(resp);
        }),
      )),
    );
}
