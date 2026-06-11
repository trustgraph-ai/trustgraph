import { Cause, Context, Effect, Fiber, Layer, Ref, Schema as S, Scope, Stream, SubscriptionRef } from "effect";
import type * as RpcGroup from "effect/unstable/rpc/RpcGroup";
import * as RpcClient from "effect/unstable/rpc/RpcClient";
import type { RpcClientError } from "effect/unstable/rpc/RpcClientError";
import * as RpcSerialization from "effect/unstable/rpc/RpcSerialization";
import * as Socket from "effect/unstable/socket/Socket";
import type { DispatchStreamChunk } from "../rpc/contract.js";
import { DispatchPayload, DispatchError, TrustGraphRpcs, } from "../rpc/contract.js";

type TrustGraphRpcClient = RpcClient.RpcClient<
  RpcGroup.Rpcs<typeof TrustGraphRpcs>,
  RpcClientError
>;

class TrustGraphRpcClientService extends Context.Service<
  TrustGraphRpcClientService,
  TrustGraphRpcClient
>()("@trustgraph/client/socket/effect-rpc-client/TrustGraphRpcClientService") {}

export type RpcConnectionStatus = "connecting" | "connected" | "failed" | "closed";

export class RpcConnectionState extends S.Class<RpcConnectionState>("RpcConnectionState")({
  status: S.Literals(["connecting", "connected", "failed", "closed"]),
  lastError: S.optionalKey(S.String),
}, { description: "Current Effect RPC gateway connection state." }) {}

export class DispatchInput extends S.Class<DispatchInput>("DispatchInput")({
  scope: S.Literals(["global", "flow"]),
  service: S.String,
  flow: S.optionalKey(S.String),
  request: S.Record(S.String, S.Unknown),
}, { description: "TrustGraph gateway dispatch target and request payload." }) {}

export interface DispatchOptions {
  readonly timeoutMs?: number;
  readonly retries?: number;
}

export interface TrustGraphGatewayClient {
  readonly state: Effect.Effect<RpcConnectionState>;
  readonly changes: Stream.Stream<RpcConnectionState>;
  readonly subscribe: (
    listener: (state: RpcConnectionState) => void,
  ) => Effect.Effect<Effect.Effect<void>>;
  readonly dispatch: (
    input: DispatchInput,
    options?: DispatchOptions,
  ) => Effect.Effect<unknown, RpcClientError | DispatchError>;
  readonly dispatchStream: (
    input: DispatchInput,
    options?: DispatchOptions,
  ) => Stream.Stream<DispatchStreamChunk, RpcClientError | DispatchError>;
  readonly runDispatchStream: (
    input: DispatchInput,
    receiver: (chunk: DispatchStreamChunk) => boolean,
    options?: DispatchOptions,
  ) => Effect.Effect<DispatchStreamChunk | undefined, RpcClientError | DispatchError>;
  readonly close: Effect.Effect<void>;
}

export class TrustGraphGatewayClientService extends Context.Service<
  TrustGraphGatewayClientService,
  TrustGraphGatewayClient
>()("@trustgraph/client/socket/effect-rpc-client/TrustGraphGatewayClientService") {}

export interface TrustGraphGatewayClientOptions {
  readonly url: string;
  readonly onConnect?: () => void;
  readonly onDisconnect?: () => void;
  readonly stateRef?: SubscriptionRef.SubscriptionRef<RpcConnectionState>;
  readonly closedRef?: Ref.Ref<boolean>;
}

const DEFAULT_REQUEST_TIMEOUT_MS = 10_000;
const DEFAULT_REQUEST_ATTEMPTS = 3;

const makeClientLayer = (
  options: TrustGraphGatewayClientOptions,
  stateRef: SubscriptionRef.SubscriptionRef<RpcConnectionState>,
  closedRef: Ref.Ref<boolean>,
): Layer.Layer<TrustGraphRpcClientService> => {
  const setState = (nextState: RpcConnectionState) =>
    SubscriptionRef.set(stateRef, nextState);

  const socketLayer = Layer.effect(
    Socket.Socket,
    Socket.makeWebSocket(options.url, {
      closeCodeIsError: (code) => code !== 1000,
      openTimeout: "10 seconds",
    }),
  ).pipe(Layer.provide(Socket.layerWebSocketConstructorGlobal));

  const hooksLayer = Layer.succeed(
    RpcClient.ConnectionHooks,
    RpcClient.ConnectionHooks.of({
      onConnect: Effect.gen(function* () {
        yield* setState({ status: "connected" });
        options.onConnect?.();
      }),
      onDisconnect: Effect.gen(function* () {
        const closed = yield* Ref.get(closedRef);
        if (!closed) {
          yield* setState({
            status: "connecting",
            lastError: "Disconnected from gateway",
          });
        }
        options.onDisconnect?.();
      }),
    }),
  );

  const protocolLayer = RpcClient.layerProtocolSocket({
    retryTransientErrors: true,
  }).pipe(
    Layer.provide(socketLayer),
    Layer.provide(RpcSerialization.layerNdjson),
    Layer.provide(hooksLayer),
  );

  return Layer.effect(
    TrustGraphRpcClientService,
    RpcClient.make(TrustGraphRpcs),
  ).pipe(Layer.provide(protocolLayer));
};

const makeSubscribeEffect = Effect.fn("makeSubscribeEffect")(function* (
    stateRef: SubscriptionRef.SubscriptionRef<RpcConnectionState>,
    scope: Scope.Scope,
    listener: (state: RpcConnectionState) => void,
  ) {
    let latest = SubscriptionRef.getUnsafe(stateRef);
    listener(latest);
    let replaySeen = false;
    const fiber = yield* Effect.forkIn(SubscriptionRef.changes(stateRef).pipe(
      Stream.runForEach((nextState) =>
        Effect.sync(() => {
          if (!replaySeen) {
            replaySeen = true;
            if (nextState === latest) return;
          }
          latest = nextState;
          listener(nextState);
        })
      ),
    ), scope);
    return yield* Effect.succeed(Fiber.interrupt(fiber).pipe(Effect.asVoid));
});

export const makeTrustGraphGatewayClientScoped: (
  options: TrustGraphGatewayClientOptions,
) => Effect.Effect<TrustGraphGatewayClient, never, Scope.Scope> = Effect.fn("makeTrustGraphGatewayClientScoped")(function* (
  options,
) {
  const stateRef = options.stateRef ?? (yield* SubscriptionRef.make<RpcConnectionState>({ status: "connecting" }));
  const closedRef = options.closedRef ?? (yield* Ref.make(false));
  const scope = yield* Scope.Scope;
  const context = yield* Layer.buildWithScope(makeClientLayer(options, stateRef, closedRef), scope).pipe(
    Effect.tapCause((cause) =>
      SubscriptionRef.set(stateRef, {
        status: "failed",
        lastError: Cause.pretty(cause),
      })
    ),
  );
  const client = Context.get(context, TrustGraphRpcClientService);

  const close = Effect.gen(function* () {
    const wasClosed = yield* Ref.getAndSet(closedRef, true);
    if (!wasClosed) {
      yield* SubscriptionRef.set(stateRef, { status: "closed" });
    }
  });

  yield* Effect.addFinalizer(() => close);

  return {
    state: SubscriptionRef.get(stateRef),
    changes: SubscriptionRef.changes(stateRef),
    subscribe: (listener) => makeSubscribeEffect(stateRef, scope, listener),
    dispatch: (input, options = {}) =>
      withDispatchRequestPolicy(client.Dispatch(DispatchPayload.make(input)), options),
    dispatchStream: (input, options = {}) =>
      Stream.unwrap(
        withDispatchRequestPolicy(
          Effect.succeed(client.DispatchStream(DispatchPayload.make(input))),
          options,
        ),
      ),
    runDispatchStream: (input, receiver, options = {}) => {
      let last: DispatchStreamChunk | undefined;
      return withDispatchRequestPolicy(
        client.DispatchStream(DispatchPayload.make(input)).pipe(
          Stream.runForEachWhile((chunk) =>
            Effect.suspend(() => {
              last = chunk;
              return Effect.succeed(!receiver(chunk));
            }),
          ),
          Effect.andThen(() => Effect.succeed(last)),
        ),
        options,
      );
    },
    close,
  } satisfies TrustGraphGatewayClient;
});

export const makeTrustGraphGatewayClientLayer = (
  options: TrustGraphGatewayClientOptions,
): Layer.Layer<TrustGraphGatewayClientService> =>
  Layer.effect(
    TrustGraphGatewayClientService,
    makeTrustGraphGatewayClientScoped(options).pipe(
      Effect.map(TrustGraphGatewayClientService.of),
    ),
  );

export function makeEffectRpcClient(
  url: string,
  onConnect?: () => void,
  onDisconnect?: () => void,
): Effect.Effect<TrustGraphGatewayClient, never, Scope.Scope> {
  return makeTrustGraphGatewayClientScoped({
    url,
    ...(onConnect === undefined ? {} : { onConnect }),
    ...(onDisconnect === undefined ? {} : { onDisconnect }),
  });
}

export function withDispatchRequestPolicy<A, E, R>(
  effect: Effect.Effect<A, E, R>,
  options: DispatchOptions,
): Effect.Effect<A, E | DispatchError, R> {
  const timeoutMs = normalizeTimeoutMs(options.timeoutMs);
  const retryTimes = normalizeAttempts(options.retries) - 1;
  const timed = effect.pipe(
    Effect.timeoutOrElse({
      duration: timeoutMs,
      orElse: () =>
        Effect.fail(
          DispatchError.make({
            message: `Request timed out after ${timeoutMs}ms`,
          }),
        ),
    }),
  );

  return retryTimes > 0 ? timed.pipe(Effect.retry({ times: retryTimes })) : timed;
}

function normalizeTimeoutMs(timeoutMs: number | undefined): number {
  if (timeoutMs === undefined || !Number.isFinite(timeoutMs) || timeoutMs <= 0) {
    return DEFAULT_REQUEST_TIMEOUT_MS;
  }
  return Math.floor(timeoutMs);
}

function normalizeAttempts(retries: number | undefined): number {
  if (retries === undefined || !Number.isFinite(retries)) {
    return DEFAULT_REQUEST_ATTEMPTS;
  }
  return Math.max(1, Math.floor(retries));
}
