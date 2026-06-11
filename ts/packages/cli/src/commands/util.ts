/**
 * Shared CLI utilities.
 */

import type {
  DispatchOptions,
  TrustGraphGatewayClient,
} from "@trustgraph/client";
import {
  makeTrustGraphGatewayClientScoped,
} from "@trustgraph/client";
import { Effect } from "effect";
import * as O from "effect/Option";
import * as S from "effect/Schema";
import * as Command from "effect/unstable/cli/Command";
import * as Flag from "effect/unstable/cli/Flag";

export class CliOpts extends S.Class<CliOpts>("CliOpts")({
  gateway: S.String,
  user: S.String,
  token: S.optionalKey(S.String),
  flow: S.String,
}, { description: "Resolved TrustGraph CLI connection options." }) {}

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

function gatewayUrlWithToken(opts: CliOpts): string {
  if (opts.token === undefined || opts.token.length === 0) return opts.gateway;
  const separator = opts.gateway.includes("?") ? "&" : "?";
  return `${opts.gateway}${separator}token=${encodeURIComponent(opts.token)}`;
}

export const withGatewayClient = Effect.fn("withGatewayClient")(function* <A, E, R>(
  use: (client: TrustGraphGatewayClient, opts: CliOpts) => Effect.Effect<A, E, R>,
) {
  const opts = yield* getOpts;
  return yield* Effect.scoped(
    makeTrustGraphGatewayClientScoped({ url: gatewayUrlWithToken(opts) }).pipe(
      Effect.flatMap((client) => use(client, opts)),
    ),
  );
});

export interface GatewayDispatchOptions {
  readonly flow?: string;
  readonly timeoutMs?: number;
  readonly retries?: number;
}

export const gatewayDispatch = Effect.fn("gatewayDispatch")(function*(
  client: TrustGraphGatewayClient,
  operation: string,
  service: string,
  request: Record<string, unknown>,
  options: GatewayDispatchOptions = {},
) {
  const input = options.flow === undefined
    ? {
        scope: "global" as const,
        service,
        request,
      }
    : {
        scope: "flow" as const,
        service,
        flow: options.flow,
        request,
      };
  const dispatchOptions: DispatchOptions = {
    ...(options.timeoutMs !== undefined ? { timeoutMs: options.timeoutMs } : {}),
    ...(options.retries !== undefined ? { retries: options.retries } : {}),
  };

  return yield* client.dispatch(input, dispatchOptions).pipe(
    Effect.mapError((error) => cliCommandError(operation, error)),
  );
});
