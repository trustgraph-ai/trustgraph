/**
 * Config CLI commands.
 *
 * Python reference: trustgraph-cli/trustgraph/cli/show_config.py etc.
 */

import { Effect } from "effect";
import * as Argument from "effect/unstable/cli/Argument";
import * as Command from "effect/unstable/cli/Command";
import { gatewayDispatch, withGatewayClient, writeJson } from "./util.js";

const show = Command.make("show", {}, () =>
  withGatewayClient((client) =>
    Effect.gen(function* () {
      const resp = yield* gatewayDispatch(client, "config.show", "config", { operation: "config" }, { timeoutMs: 60000 });
      yield* writeJson(resp);
    }),
  ),
).pipe(Command.withDescription("Show current configuration"));

const get = Command.make("get", {
  key: Argument.string("key").pipe(Argument.withDescription("Config key (format: type/key)")),
}, ({ key }) =>
  withGatewayClient((client) =>
    Effect.gen(function* () {
      const parts = key.split("/");
      const configKey =
        parts.length >= 2
          ? { type: parts[0], key: parts.slice(1).join("/") }
          : { type: "config", key };
      const resp = yield* gatewayDispatch(client, "config.get", "config", {
        operation: "get",
        keys: [configKey],
      }, { timeoutMs: 60000 });
      yield* writeJson(resp);
    }),
  ),
).pipe(Command.withDescription("Get a configuration value"));

const set = Command.make("set", {
  key: Argument.string("key").pipe(Argument.withDescription("Config key (format: type/key)")),
  value: Argument.string("value").pipe(Argument.withDescription("Config value (JSON)")),
}, ({ key, value }) =>
  withGatewayClient((client) =>
    Effect.gen(function* () {
      const parts = key.split("/");
      const configEntry =
        parts.length >= 2
          ? { type: parts[0], key: parts.slice(1).join("/"), value }
          : { type: "config", key, value };
      const resp = yield* gatewayDispatch(client, "config.set", "config", {
        operation: "put",
        values: [configEntry],
      }, { timeoutMs: 60000 });
      yield* writeJson(resp);
    }),
  ),
).pipe(Command.withDescription("Set a configuration value"));

const list = Command.make("list", {
  type: Argument.string("type").pipe(
    Argument.withDescription("Config type to list"),
    Argument.withDefault("config"),
  ),
}, ({ type }) =>
  withGatewayClient((client) =>
    Effect.gen(function* () {
      const resp = yield* gatewayDispatch(client, "config.list", "config", {
        operation: "list",
        type,
      }, { timeoutMs: 60000 });
      yield* writeJson(resp);
    }),
  ),
).pipe(Command.withDescription("List configuration keys for a type"));

const deleteCommand = Command.make("delete", {
  key: Argument.string("key").pipe(Argument.withDescription("Config key (format: type/key)")),
}, ({ key }) =>
  withGatewayClient((client) =>
    Effect.gen(function* () {
      const parts = key.split("/");
      const configKey =
        parts.length >= 2
          ? { type: parts[0], key: parts.slice(1).join("/") }
          : { type: "config", key };
      const resp = yield* gatewayDispatch(client, "config.delete", "config", {
        operation: "delete",
        keys: [configKey],
      }, { timeoutMs: 30000 });
      yield* writeJson(resp);
    }),
  ),
).pipe(Command.withDescription("Delete a configuration entry"));

export const configCommand = Command.make("config").pipe(
  Command.withDescription("Configuration management"),
  Command.withSubcommands([show, get, set, list, deleteCommand]),
);
