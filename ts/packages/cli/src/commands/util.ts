/**
 * Shared CLI utilities.
 */

import type { Command } from "commander";
import { createTrustGraphSocket, type BaseApi } from "@trustgraph/client";
import { Duration, Effect } from "effect";
import * as S from "effect/Schema";

export interface CliOpts {
  gateway: string;
  user: string;
  token?: string;
  flow: string;
}

export function getOpts(cmd: Command): CliOpts {
  // Walk up to root command to get global options
  let root = cmd;
  while (root.parent !== null) root = root.parent;
  return root.opts() as CliOpts;
}

export class CliCommandError extends S.TaggedErrorClass<CliCommandError>()(
  "CliCommandError",
  {
    message: S.String,
    operation: S.String,
  },
) {}

export function cliCommandError(operation: string, error: unknown): CliCommandError {
  const message = typeof error === "object" && error !== null && "message" in error
    ? String(error.message)
    : String(error);
  return CliCommandError.make({ operation, message });
}

export const writeLine = (line: string) =>
  Effect.sync(() => {
    process.stdout.write(`${line}\n`);
  });

export const writeJson = (value: unknown) =>
  S.encodeUnknownEffect(S.UnknownFromJsonString)(value).pipe(
    Effect.mapError((error) => cliCommandError("write-json", error)),
    Effect.flatMap(writeLine),
  );

/**
 * Create a BaseApi socket client and wait for the connection to be established.
 * The client auto-connects; we listen for the first "connected/authenticated"
 * state before handing it back to the caller.
 */
export function createSocketEffect(opts: CliOpts): Effect.Effect<BaseApi, CliCommandError> {
  const socket = createTrustGraphSocket(opts.user, opts.token, opts.gateway);

  return Effect.callback<void, CliCommandError>((resume) => {
    const unsub = socket.onConnectionStateChange((state) => {
      if (state.status === "authenticated" || state.status === "unauthenticated") {
        unsub();
        resume(Effect.void);
      } else if (state.status === "failed") {
        unsub();
        resume(Effect.fail(cliCommandError("connect", state.lastError ?? "WebSocket connection failed")));
      }
    });

    return Effect.sync(() => {
      unsub();
    });
  }).pipe(
    Effect.timeout(Duration.seconds(15)),
    Effect.catchTag("TimeoutError", () =>
      Effect.fail(cliCommandError("connect", "Timed out waiting for WebSocket connection")),
    ),
    Effect.as(socket),
  );
}

export function createSocket(opts: CliOpts): Promise<BaseApi> {
  return Effect.runPromise(createSocketEffect(opts));
}

export const withSocket = <A, E, R>(
  cmd: Command,
  use: (socket: BaseApi, opts: CliOpts) => Effect.Effect<A, E, R>,
) =>
  Effect.acquireUseRelease(
    createSocketEffect(getOpts(cmd)),
    (socket) => use(socket, getOpts(cmd)),
    (socket) =>
      Effect.sync(() => {
        socket.close();
      }),
  );
