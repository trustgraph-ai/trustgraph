/**
 * Shared CLI utilities.
 */

import { createTrustGraphSocket, type BaseApi } from "@trustgraph/client";
import { Duration, Effect } from "effect";
import * as O from "effect/Option";
import * as S from "effect/Schema";
import * as Command from "effect/unstable/cli/Command";
import * as Flag from "effect/unstable/cli/Flag";

export interface CliOpts {
  gateway: string;
  user: string;
  token?: string;
  flow: string;
}

export const rootCommand = Command.make("tg").pipe(
  Command.withDescription("TrustGraph CLI - interact with TrustGraph services"),
  Command.withSharedFlags({
    gateway: Flag.string("gateway").pipe(
      Flag.withAlias("g"),
      Flag.withDescription("Gateway WebSocket URL"),
      Flag.withDefault("ws://localhost:8088/api/v1/rpc"),
    ),
    user: Flag.string("user").pipe(
      Flag.withAlias("u"),
      Flag.withDescription("User identifier"),
      Flag.withDefault("cli"),
    ),
    token: Flag.string("token").pipe(
      Flag.withAlias("t"),
      Flag.withDescription("Authentication token"),
      Flag.optional,
    ),
    flow: Flag.string("flow").pipe(
      Flag.withAlias("f"),
      Flag.withDescription("Flow ID"),
      Flag.withDefault("default"),
    ),
  }),
);

export const getOpts = Effect.gen(function* () {
  const opts = yield* rootCommand;
  const base = {
    gateway: opts.gateway,
    user: opts.user,
    flow: opts.flow,
  };
  const token = O.getOrUndefined(opts.token);
  return token === undefined ? base : { ...base, token } satisfies CliOpts;
});

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

export const withSocket = Effect.fn("withSocket")(function* <A, E, R>(
  use: (socket: BaseApi, opts: CliOpts) => Effect.Effect<A, E, R>,
) {
  const opts = yield* getOpts;
  return yield* Effect.acquireUseRelease(
    createSocketEffect(opts),
    (socket) => use(socket, opts),
    (socket) =>
      Effect.sync(() => {
        socket.close();
      }),
  );
});
