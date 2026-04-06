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
        const resp = await socket.request("config", { operation: "config" });
        console.log(JSON.stringify(resp, null, 2));
      } finally {
        await socket.close();
      }
    });

  config
    .command("get")
    .description("Get a configuration value")
    .argument("<key>", "Config key")
    .action(async (key: string, _opts, cmd) => {
      const opts = getOpts(cmd);
      const socket = await createSocket(opts);

      try {
        const resp = await socket.request("config", { operation: "get", keys: [key] });
        console.log(JSON.stringify(resp, null, 2));
      } finally {
        await socket.close();
      }
    });

  config
    .command("set")
    .description("Set a configuration value")
    .argument("<key>", "Config key")
    .argument("<value>", "Config value (JSON)")
    .action(async (key: string, value: string, _opts, cmd) => {
      const opts = getOpts(cmd);
      const socket = await createSocket(opts);

      try {
        const parsed = JSON.parse(value);
        const resp = await socket.request("config", {
          operation: "put",
          values: { [key]: parsed },
        });
        console.log(JSON.stringify(resp, null, 2));
      } finally {
        await socket.close();
      }
    });

  config
    .command("list")
    .description("List configuration keys")
    .action(async (_opts, cmd) => {
      const opts = getOpts(cmd);
      const socket = await createSocket(opts);

      try {
        const resp = await socket.request("config", { operation: "list" });
        console.log(JSON.stringify(resp, null, 2));
      } finally {
        await socket.close();
      }
    });
}
