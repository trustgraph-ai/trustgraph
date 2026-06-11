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
import { cliCommandError, gatewayDispatch, withGatewayClient, writeJson } from "./util.js";

const list = Command.make("list", {}, () =>
  withGatewayClient((client) =>
    Effect.gen(function* () {
      const response = yield* gatewayDispatch(client, "flow.list", "flow", { operation: "list-flows" }, { timeoutMs: 60000 });
      const record = response as Record<string, unknown>;
      const ids = Array.isArray(record["flow-ids"]) ? record["flow-ids"] : [];
      yield* writeJson(ids);
    }),
  ),
).pipe(Command.withDescription("List active flows"));

const get = Command.make("get", {
  id: Argument.string("id").pipe(Argument.withDescription("Flow ID")),
}, ({ id }) =>
  withGatewayClient((client) =>
    Effect.gen(function* () {
      const response = yield* gatewayDispatch(client, "flow.get", "flow", {
        operation: "get-flow",
        "flow-id": id,
      }, { timeoutMs: 60000 });
      const record = response as Record<string, unknown>;
      const def = typeof record.flow === "string"
        ? yield* S.decodeUnknownEffect(S.UnknownFromJsonString)(record.flow)
        : record.flow;
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
  withGatewayClient((client) =>
    Effect.gen(function* () {
      const rawParameters = parameters._tag === "Some" ? parameters.value : undefined;
      const params = rawParameters !== undefined && rawParameters.length > 0
              ? yield* S.decodeUnknownEffect(S.UnknownFromJsonString)(rawParameters).pipe(
              Effect.flatMap(S.decodeUnknownEffect(S.Record(S.String, S.Unknown))),
              Effect.mapError((error) => cliCommandError("flow.start.parameters", error)),
            )
          : undefined;
      const request = {
        operation: "start-flow",
        "flow-id": id,
        "blueprint-name": blueprint,
        description,
        ...(params !== undefined && Object.keys(params).length > 0 ? { parameters: params } : {}),
      };
      const resp = yield* gatewayDispatch(client, "flow.start", "flow", request, { timeoutMs: 30000 });
      yield* writeJson(resp);
    }),
  ),
).pipe(Command.withDescription("Start a flow"));

const stop = Command.make("stop", {
  id: Argument.string("id").pipe(Argument.withDescription("Flow ID")),
}, ({ id }) =>
  withGatewayClient((client) =>
    Effect.gen(function* () {
      const resp = yield* gatewayDispatch(client, "flow.stop", "flow", {
        operation: "stop-flow",
        "flow-id": id,
      }, { timeoutMs: 30000 });
      yield* writeJson(resp);
    }),
  ),
).pipe(Command.withDescription("Stop a flow"));

export const flowCommand = Command.make("flow").pipe(
  Command.withDescription("Flow management"),
  Command.withSubcommands([list, get, start, stop]),
);
