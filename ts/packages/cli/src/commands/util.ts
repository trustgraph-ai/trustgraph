/**
 * Shared CLI utilities.
 */

import type { Command } from "commander";
import { SocketManager } from "@trustgraph/mcp";

export interface CliOpts {
  gateway: string;
  token?: string;
  flow: string;
}

export function getOpts(cmd: Command): CliOpts {
  // Walk up to root command to get global options
  let root = cmd;
  while (root.parent) root = root.parent;
  return root.opts() as CliOpts;
}

export async function createSocket(opts: CliOpts): Promise<SocketManager> {
  const socket = new SocketManager({
    gatewayUrl: opts.gateway,
    token: opts.token,
  });
  await socket.connect();
  return socket;
}
