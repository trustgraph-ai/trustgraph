/**
 * Flow management CLI commands.
 *
 * Python reference: trustgraph-cli/trustgraph/cli/start_flow.py, stop_flow.py, etc.
 */

import type { Command } from "commander";
import { createSocket, getOpts } from "./util.js";

export function registerFlowCommands(program: Command): void {
  const flow = program
    .command("flow")
    .description("Flow management");

  flow
    .command("list")
    .description("List active flows")
    .action(async (_opts, cmd) => {
      const opts = getOpts(cmd);
      const socket = await createSocket(opts);

      try {
        const resp = await socket.request("flow", { operation: "list" });
        console.log(JSON.stringify(resp, null, 2));
      } finally {
        await socket.close();
      }
    });

  flow
    .command("start")
    .description("Start a flow")
    .argument("<name>", "Flow name")
    .action(async (name: string, _opts, cmd) => {
      const opts = getOpts(cmd);
      const socket = await createSocket(opts);

      try {
        const resp = await socket.request("flow", { operation: "start", name });
        console.log(JSON.stringify(resp, null, 2));
      } finally {
        await socket.close();
      }
    });

  flow
    .command("stop")
    .description("Stop a flow")
    .argument("<name>", "Flow name")
    .action(async (name: string, _opts, cmd) => {
      const opts = getOpts(cmd);
      const socket = await createSocket(opts);

      try {
        const resp = await socket.request("flow", { operation: "stop", name });
        console.log(JSON.stringify(resp, null, 2));
      } finally {
        await socket.close();
      }
    });

  flow
    .command("status")
    .description("Show flow status")
    .argument("[name]", "Flow name (all if omitted)")
    .action(async (name: string | undefined, _opts, cmd) => {
      const opts = getOpts(cmd);
      const socket = await createSocket(opts);

      try {
        const resp = await socket.request("flow", {
          operation: "status",
          ...(name ? { name } : {}),
        });
        console.log(JSON.stringify(resp, null, 2));
      } finally {
        await socket.close();
      }
    });
}
