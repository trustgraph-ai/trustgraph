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
        const flows = socket.flows();
        const ids = await flows.getFlows();
        console.log(JSON.stringify(ids, null, 2));
      } finally {
        socket.close();
      }
    });

  flow
    .command("get")
    .description("Get a flow definition")
    .argument("<id>", "Flow ID")
    .action(async (id: string, _opts, cmd) => {
      const opts = getOpts(cmd);
      const socket = await createSocket(opts);

      try {
        const flows = socket.flows();
        const def = await flows.getFlow(id);
        console.log(JSON.stringify(def, null, 2));
      } finally {
        socket.close();
      }
    });

  flow
    .command("start")
    .description("Start a flow")
    .argument("<id>", "Flow ID")
    .requiredOption("-b, --blueprint <name>", "Blueprint name")
    .option("-d, --description <text>", "Flow description", "")
    .option("-p, --parameters <json>", "Parameters as JSON")
    .action(async (id: string, cmdOpts, cmd) => {
      const opts = getOpts(cmd);
      const socket = await createSocket(opts);

      try {
        const flows = socket.flows();
        const params = cmdOpts.parameters
          ? JSON.parse(cmdOpts.parameters as string)
          : undefined;
        const resp = await flows.startFlow(
          id,
          cmdOpts.blueprint as string,
          cmdOpts.description as string,
          params as Record<string, unknown> | undefined,
        );
        console.log(JSON.stringify(resp, null, 2));
      } finally {
        socket.close();
      }
    });

  flow
    .command("stop")
    .description("Stop a flow")
    .argument("<id>", "Flow ID")
    .action(async (id: string, _opts, cmd) => {
      const opts = getOpts(cmd);
      const socket = await createSocket(opts);

      try {
        const flows = socket.flows();
        const resp = await flows.stopFlow(id);
        console.log(JSON.stringify(resp, null, 2));
      } finally {
        socket.close();
      }
    });
}
