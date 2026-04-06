/**
 * Shared CLI utilities.
 */

import type { Command } from "commander";
import { createTrustGraphSocket, type BaseApi } from "@trustgraph/client";

export interface CliOpts {
  gateway: string;
  user: string;
  token?: string;
  flow: string;
}

export function getOpts(cmd: Command): CliOpts {
  // Walk up to root command to get global options
  let root = cmd;
  while (root.parent) root = root.parent;
  return root.opts() as CliOpts;
}

/**
 * Create a BaseApi socket client and wait for the connection to be established.
 * The client auto-connects; we listen for the first "connected/authenticated"
 * state before handing it back to the caller.
 */
export async function createSocket(opts: CliOpts): Promise<BaseApi> {
  const socket = createTrustGraphSocket(opts.user, opts.token, opts.gateway);

  // Wait for the socket to reach an open state
  await new Promise<void>((resolve, reject) => {
    const timeout = setTimeout(() => {
      unsub();
      reject(new Error("Timed out waiting for WebSocket connection"));
    }, 15_000);

    const unsub = socket.onConnectionStateChange((state) => {
      if (
        state.status === "authenticated" ||
        state.status === "unauthenticated"
      ) {
        clearTimeout(timeout);
        unsub();
        resolve();
      } else if (state.status === "failed") {
        clearTimeout(timeout);
        unsub();
        reject(new Error(state.lastError ?? "WebSocket connection failed"));
      }
    });
  });

  return socket;
}
