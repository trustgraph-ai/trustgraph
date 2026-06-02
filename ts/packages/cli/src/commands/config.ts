/**
 * Config CLI commands.
 *
 * Python reference: trustgraph-cli/trustgraph/cli/show_config.py etc.
 */

import type { Command } from "commander";
import { Effect } from "effect";
import { cliCommandError, withSocket, writeJson } from "./util.js";

export function registerConfigCommands(program: Command): void {
  const config = program
    .command("config")
    .description("Configuration management");

  config
    .command("show")
    .description("Show current configuration")
    .action((_opts, cmd) =>
      Effect.runPromise(withSocket(cmd, (socket) =>
        Effect.gen(function* () {
        const cfg = socket.config();
          const resp = yield* Effect.tryPromise({
            try: () => cfg.getConfigAll(),
            catch: (error) => cliCommandError("config.show", error),
          });
          yield* writeJson(resp);
        }),
      )),
    );

  config
    .command("get")
    .description("Get a configuration value")
    .argument("<key>", "Config key (format: type/key)")
    .action((key: string, _opts, cmd) =>
      Effect.runPromise(withSocket(cmd, (socket) =>
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
      )),
    );

  config
    .command("set")
    .description("Set a configuration value")
    .argument("<key>", "Config key (format: type/key)")
    .argument("<value>", "Config value (JSON)")
    .action((key: string, value: string, _opts, cmd) =>
      Effect.runPromise(withSocket(cmd, (socket) =>
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
      )),
    );

  config
    .command("list")
    .description("List configuration keys for a type")
    .argument("[type]", "Config type to list", "config")
    .action((type: string, _opts, cmd) =>
      Effect.runPromise(withSocket(cmd, (socket) =>
        Effect.gen(function* () {
        const cfg = socket.config();
          const resp = yield* Effect.tryPromise({
            try: () => cfg.list(type),
            catch: (error) => cliCommandError("config.list", error),
          });
          yield* writeJson(resp);
        }),
      )),
    );

  config
    .command("delete")
    .description("Delete a configuration entry")
    .argument("<key>", "Config key (format: type/key)")
    .action((key: string, _opts, cmd) =>
      Effect.runPromise(withSocket(cmd, (socket) =>
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
      )),
    );
}
