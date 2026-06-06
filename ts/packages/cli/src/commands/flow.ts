/**
 * Flow management CLI commands.
 *
 * Python reference: trustgraph-cli/trustgraph/cli/start_flow.py, stop_flow.py, etc.
 */

import { Effect } from "effect";
import * as S from "effect/Schema";
import * as Argument from "effect/unstable/cli/Argument";
import * as Command from "effect/unstable/cli/Command";
import * as Flag from "effect/unstable/cli/Flag";
import { cliCommandError, withSocket, writeJson } from "./util.js";

const list = Command.make("list", {}, () =>
  withSocket((socket) =>
    Effect.gen(function* () {
        const flows = socket.flows();
      const ids = yield* Effect.tryPromise({
        try: () => flows.getFlows(),
        catch: (error) => cliCommandError("flow.list", error),
      });
      yield* writeJson(ids);
    }),
  ),
).pipe(Command.withDescription("List active flows"));

const get = Command.make("get", {
  id: Argument.string("id").pipe(Argument.withDescription("Flow ID")),
}, ({ id }) =>
  withSocket((socket) =>
    Effect.gen(function* () {
        const flows = socket.flows();
      const def = yield* Effect.tryPromise({
        try: () => flows.getFlow(id),
        catch: (error) => cliCommandError("flow.get", error),
      });
      yield* writeJson(def);
    }),
  ),
).pipe(Command.withDescription("Get a flow definition"));

const start = Command.make("start", {
  id: Argument.string("id").pipe(Argument.withDescription("Flow ID")),
  blueprint: Flag.string("blueprint").pipe(
    Flag.withAlias("b"),
    Flag.withDescription("Blueprint name"),
  ),
  description: Flag.string("description").pipe(
    Flag.withAlias("d"),
    Flag.withDescription("Flow description"),
    Flag.withDefault(""),
  ),
  parameters: Flag.string("parameters").pipe(
    Flag.withAlias("p"),
    Flag.withDescription("Parameters as JSON"),
    Flag.optional,
  ),
}, ({ id, blueprint, description, parameters }) =>
  withSocket((socket) =>
    Effect.gen(function* () {
        const flows = socket.flows();
      const rawParameters = parameters._tag === "Some" ? parameters.value : undefined;
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
            blueprint,
            description,
            params,
          ),
        catch: (error) => cliCommandError("flow.start", error),
      });
      yield* writeJson(resp);
    }),
  ),
).pipe(Command.withDescription("Start a flow"));

const stop = Command.make("stop", {
  id: Argument.string("id").pipe(Argument.withDescription("Flow ID")),
}, ({ id }) =>
  withSocket((socket) =>
    Effect.gen(function* () {
        const flows = socket.flows();
      const resp = yield* Effect.tryPromise({
        try: () => flows.stopFlow(id),
        catch: (error) => cliCommandError("flow.stop", error),
      });
      yield* writeJson(resp);
    }),
  ),
).pipe(Command.withDescription("Stop a flow"));

export const flowCommand = Command.make("flow").pipe(
  Command.withDescription("Flow management"),
  Command.withSubcommands([list, get, start, stop]),
);
