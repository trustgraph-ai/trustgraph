/**
 * Config CLI commands.
 *
 * Python reference: trustgraph-cli/trustgraph/cli/show_config.py etc.
 */

import { Effect } from "effect";
import * as Argument from "effect/unstable/cli/Argument";
import * as Command from "effect/unstable/cli/Command";
import { cliCommandError, withSocket, writeJson } from "./util.js";

const show = Command.make("show", {}, () =>
  withSocket((socket) =>
    Effect.gen(function* () {
        const cfg = socket.config();
      const resp = yield* Effect.tryPromise({
        try: () => cfg.getConfigAll(),
        catch: (error) => cliCommandError("config.show", error),
      });
      yield* writeJson(resp);
    }),
  ),
).pipe(Command.withDescription("Show current configuration"));

const get = Command.make("get", {
  key: Argument.string("key").pipe(Argument.withDescription("Config key (format: type/key)")),
}, ({ key }) =>
  withSocket((socket) =>
    Effect.gen(function* () {
        const cfg = socket.config();
        // Support "type/key" format; fall back to using the whole string as key
        const parts = key.split("/");
        const configKey =
          parts.length >= 2
            ? { type: parts[0], key: parts.slice(1).join("/") }
            : { type: "config", key };
      const resp = yield* Effect.tryPromise({
        try: () => cfg.getConfig([configKey]),
        catch: (error) => cliCommandError("config.get", error),
      });
      yield* writeJson(resp);
    }),
  ),
).pipe(Command.withDescription("Get a configuration value"));

const set = Command.make("set", {
  key: Argument.string("key").pipe(Argument.withDescription("Config key (format: type/key)")),
  value: Argument.string("value").pipe(Argument.withDescription("Config value (JSON)")),
}, ({ key, value }) =>
  withSocket((socket) =>
    Effect.gen(function* () {
        const cfg = socket.config();
        const parts = key.split("/");
        const configEntry =
          parts.length >= 2
            ? { type: parts[0], key: parts.slice(1).join("/"), value }
            : { type: "config", key, value };
      const resp = yield* Effect.tryPromise({
        try: () => cfg.putConfig([configEntry]),
        catch: (error) => cliCommandError("config.set", error),
      });
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
  withSocket((socket) =>
    Effect.gen(function* () {
        const cfg = socket.config();
      const resp = yield* Effect.tryPromise({
        try: () => cfg.list(type),
        catch: (error) => cliCommandError("config.list", error),
      });
      yield* writeJson(resp);
    }),
  ),
).pipe(Command.withDescription("List configuration keys for a type"));

const deleteCommand = Command.make("delete", {
  key: Argument.string("key").pipe(Argument.withDescription("Config key (format: type/key)")),
}, ({ key }) =>
  withSocket((socket) =>
    Effect.gen(function* () {
        const cfg = socket.config();
        const parts = key.split("/");
        const configKey =
          parts.length >= 2
            ? { type: parts[0], key: parts.slice(1).join("/") }
            : { type: "config", key };
      const resp = yield* Effect.tryPromise({
        try: () => cfg.deleteConfig(configKey),
        catch: (error) => cliCommandError("config.delete", error),
      });
      yield* writeJson(resp);
    }),
  ),
).pipe(Command.withDescription("Delete a configuration entry"));

export const configCommand = Command.make("config").pipe(
  Command.withDescription("Configuration management"),
  Command.withSubcommands([show, get, set, list, deleteCommand]),
);
