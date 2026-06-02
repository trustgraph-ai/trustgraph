import { Cause, Context, Effect, Layer, ManagedRuntime, Stream } from "effect";
import type * as RpcGroup from "effect/unstable/rpc/RpcGroup";
import * as RpcClient from "effect/unstable/rpc/RpcClient";
import type { RpcClientError } from "effect/unstable/rpc/RpcClientError";
import * as RpcSerialization from "effect/unstable/rpc/RpcSerialization";
import * as Socket from "effect/unstable/socket/Socket";
import { DispatchPayload, DispatchError, TrustGraphRpcs, type DispatchStreamChunk } from "../rpc/contract.js";

type TrustGraphRpcClient = RpcClient.RpcClient<
  RpcGroup.Rpcs<typeof TrustGraphRpcs>,
  RpcClientError
>;

class TrustGraphRpcClientService extends Context.Service<
  TrustGraphRpcClientService,
  TrustGraphRpcClient
>()("@trustgraph/client/socket/effect-rpc-client/TrustGraphRpcClientService") {}

export type RpcConnectionStatus = "connecting" | "connected" | "failed" | "closed";

export interface RpcConnectionState {
  status: RpcConnectionStatus;
  lastError?: string;
}

export interface DispatchInput {
  scope: "global" | "flow";
  service: string;
  flow?: string;
  request: Record<string, unknown>;
}

export interface DispatchOptions {
  readonly timeoutMs?: number;
  readonly retries?: number;
}

const DEFAULT_REQUEST_TIMEOUT_MS = 10_000;
const DEFAULT_REQUEST_ATTEMPTS = 3;

type NewableFactory<Args extends readonly unknown[], A extends object> = {
  new (...args: Args): A;
  (...args: Args): A;
  readonly prototype: A;
};

function newableFactory<Args extends readonly unknown[], A extends object>(
  factory: (...args: Args) => A,
): NewableFactory<Args, A> {
  function Constructor(...args: Args): A {
    return factory(...args);
  }
  return Constructor as unknown as NewableFactory<Args, A>;
}

export interface EffectRpcClient {
  readonly subscribe: (listener: (state: RpcConnectionState) => void) => () => void;
  readonly dispatch: (
    input: DispatchInput,
    options?: DispatchOptions,
  ) => Promise<unknown>;
  readonly dispatchStream: (
    input: DispatchInput,
    receiver: (chunk: DispatchStreamChunk) => boolean,
    options?: DispatchOptions,
  ) => Promise<DispatchStreamChunk | undefined>;
  readonly close: () => Promise<void>;
}

export function makeEffectRpcClient(
  url: string,
  onConnect?: () => void,
  onDisconnect?: () => void,
): EffectRpcClient {
  const listeners = new Set<(state: RpcConnectionState) => void>();
  let state: RpcConnectionState = { status: "connecting" };
  let closed = false;

  const setState = (nextState: RpcConnectionState): void => {
    state = nextState;
    for (const listener of listeners) {
      listener(nextState);
    }
  };

  const makeClientLayer = (): Layer.Layer<TrustGraphRpcClientService> => {
    const socketLayer = Layer.effect(
      Socket.Socket,
      Socket.makeWebSocket(url, {
        closeCodeIsError: (code) => code !== 1000,
        openTimeout: "10 seconds",
      }),
    ).pipe(Layer.provide(Socket.layerWebSocketConstructorGlobal));

    const hooksLayer = Layer.succeed(
      RpcClient.ConnectionHooks,
      RpcClient.ConnectionHooks.of({
        onConnect: Effect.sync(() => {
          setState({ status: "connected" });
          onConnect?.();
        }),
        onDisconnect: Effect.sync(() => {
          if (!closed) {
            setState({
              status: "connecting",
              lastError: "Disconnected from gateway",
            });
          }
          onDisconnect?.();
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

    const clientLayer = Layer.effect(
      TrustGraphRpcClientService,
      RpcClient.make(TrustGraphRpcs),
    ).pipe(Layer.provide(protocolLayer));

    return clientLayer;
  };

  const runtime = ManagedRuntime.make(makeClientLayer());
  const clientPromise = runtime.runPromise(
    TrustGraphRpcClientService.pipe(
      Effect.tapCause((cause) =>
        Effect.sync(() => {
          setState({
            status: "failed",
            lastError: Cause.pretty(cause),
          });
        })
      ),
    ),
  );

  return {
    subscribe: (listener) => {
      listeners.add(listener);
      listener(state);
      return () => {
        listeners.delete(listener);
      };
    },
    dispatch: (input, options = {}) =>
      clientPromise.then((client) =>
        runtime.runPromise(
          withDispatchRequestPolicy(client.Dispatch(DispatchPayload.make(input)), options),
        )
      ),
    dispatchStream: (input, receiver, options = {}) => {
      let last: DispatchStreamChunk | undefined;
      return clientPromise.then((client) =>
        runtime.runPromise(
          withDispatchRequestPolicy(
            client.DispatchStream(DispatchPayload.make(input)).pipe(
              Stream.runForEachWhile((chunk) =>
                Effect.suspend(() => {
                  last = chunk;
                  return Effect.succeed(!receiver(chunk));
                }),
              ),
            ),
            options,
          ),
        )
      ).then(() => last);
    },
    close: () => {
      if (closed) return Promise.resolve();
      closed = true;
      setState({ status: "closed" });
      return runtime.dispose();
    },
  };
}

export const EffectRpcClient = newableFactory(makeEffectRpcClient);

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
