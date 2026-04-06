/**
 * Config CLI commands.
 *
 * Python reference: trustgraph-cli/trustgraph/cli/show_config.py etc.
 */

import type { Command } from "commander";
import { createSocket, getOpts } from "./util.js";

export function registerConfigCommands(program: Command): void {
  const config = program
    .command("config")
    .description("Configuration management");

  config
    .command("show")
    .description("Show current configuration")
    .action(async (_opts, cmd) => {
      const opts = getOpts(cmd);
      const socket = await createSocket(opts);

      try {
        const cfg = socket.config();
        const resp = await cfg.getConfigAll();
        console.log(JSON.stringify(resp, null, 2));
      } finally {
        socket.close();
      }
    });

  config
    .command("get")
    .description("Get a configuration value")
    .argument("<key>", "Config key (format: type/key)")
    .action(async (key: string, _opts, cmd) => {
      const opts = getOpts(cmd);
      const socket = await createSocket(opts);

      try {
        const cfg = socket.config();
        // Support "type/key" format; fall back to using the whole string as key
        const parts = key.split("/");
        const configKey =
          parts.length >= 2
            ? { type: parts[0], key: parts.slice(1).join("/") }
            : { type: "config", key };
        const resp = await cfg.getConfig([configKey]);
        console.log(JSON.stringify(resp, null, 2));
      } finally {
        socket.close();
      }
    });

  config
    .command("set")
    .description("Set a configuration value")
    .argument("<key>", "Config key (format: type/key)")
    .argument("<value>", "Config value (JSON)")
    .action(async (key: string, value: string, _opts, cmd) => {
      const opts = getOpts(cmd);
      const socket = await createSocket(opts);

      try {
        const cfg = socket.config();
        const parts = key.split("/");
        const configEntry =
          parts.length >= 2
            ? { type: parts[0], key: parts.slice(1).join("/"), value }
            : { type: "config", key, value };
        const resp = await cfg.putConfig([configEntry]);
        console.log(JSON.stringify(resp, null, 2));
      } finally {
        socket.close();
      }
    });

  config
    .command("list")
    .description("List configuration keys for a type")
    .argument("[type]", "Config type to list", "config")
    .action(async (type: string, _opts, cmd) => {
      const opts = getOpts(cmd);
      const socket = await createSocket(opts);

      try {
        const cfg = socket.config();
        const resp = await cfg.list(type);
        console.log(JSON.stringify(resp, null, 2));
      } finally {
        socket.close();
      }
    });

  config
    .command("delete")
    .description("Delete a configuration entry")
    .argument("<key>", "Config key (format: type/key)")
    .action(async (key: string, _opts, cmd) => {
      const opts = getOpts(cmd);
      const socket = await createSocket(opts);

      try {
        const cfg = socket.config();
        const parts = key.split("/");
        const configKey =
          parts.length >= 2
            ? { type: parts[0], key: parts.slice(1).join("/") }
            : { type: "config", key };
        const resp = await cfg.deleteConfig(configKey);
        console.log(JSON.stringify(resp, null, 2));
      } finally {
        socket.close();
      }
    });
}
