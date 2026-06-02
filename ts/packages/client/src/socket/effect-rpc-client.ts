import { Context, Data, Effect, Exit, Layer, Scope, Stream } from "effect";
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

  const makeClient = (): Effect.Effect<TrustGraphRpcClient, never, Scope.Scope> => {
    const socketLayer = Layer.effect(
      Socket.Socket,
      Socket.makeWebSocket(url, {
        closeCodeIsError: (code) => code !== 1000,
        openTimeout: "10 seconds",
      }),
    ).pipe(Layer.provide(webSocketConstructorLayer));

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

    return Effect.map(
      Layer.build(clientLayer),
      (context) => Context.get(context, TrustGraphRpcClientService),
    );
  };

  const scopePromise = Effect.runPromise(Scope.make());
  const clientPromise = scopePromise.then((scope) =>
    Effect.runPromise(makeClient().pipe(Scope.provide(scope))),
  );
  clientPromise.catch((cause) => {
    setState({
      status: "failed",
      lastError: errorMessage(cause),
    });
  });

  return {
    subscribe: (listener) => {
      listeners.add(listener);
      listener(state);
      return () => {
        listeners.delete(listener);
      };
    },
    dispatch: async (input, options = {}) => {
      const client = await clientPromise;
      return await Effect.runPromise(
        withDispatchRequestPolicy(client.Dispatch(new DispatchPayload(input)), options),
      );
    },
    dispatchStream: async (input, receiver, options = {}) => {
      const client = await clientPromise;
      let last: DispatchStreamChunk | undefined;
      await Effect.runPromise(
        withDispatchRequestPolicy(
          client.DispatchStream(new DispatchPayload(input)).pipe(
            Stream.runForEach((chunk) =>
              Effect.suspend(() => {
                last = chunk;
                if (receiver(chunk)) return Effect.fail(new StopStreaming());
                return Effect.void;
              }),
            ),
            Effect.catchIf(
              (cause): cause is StopStreaming => cause instanceof StopStreaming,
              () => Effect.void,
            ),
          ),
          options,
        ),
      );
      return last;
    },
    close: async () => {
      if (closed) return;
      closed = true;
      setState({ status: "closed" });
      const scope = await scopePromise;
      await Effect.runPromise(Scope.close(scope, Exit.void));
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
          new DispatchError({
            message: `Request timed out after ${timeoutMs}ms`,
          }),
        ),
    }),
  );

  return retryTimes > 0 ? timed.pipe(Effect.retry({ times: retryTimes })) : timed;
}

class StopStreaming extends Data.TaggedError("StopStreaming")<{}> {}

const webSocketConstructorLayer: Layer.Layer<Socket.WebSocketConstructor> = Layer.effect(
  Socket.WebSocketConstructor,
  Effect.promise(async () => {
    if (typeof globalThis !== "undefined" && "WebSocket" in globalThis) {
      return (url, protocols) => new globalThis.WebSocket(url, protocols);
    }

    try {
      const mod = await import("ws");
      const WS = mod.WebSocket;
      return (url, protocols) => new WS(url, protocols) as unknown as globalThis.WebSocket;
    } catch (cause) {
      throw new DispatchError({
        message: `WebSocket is not available: ${errorMessage(cause)}`,
      });
    }
  }),
);

function errorMessage(cause: unknown): string {
  if (cause instanceof Error) return cause.message;
  if (typeof cause === "string") return cause;
  if (cause !== null && typeof cause === "object" && "message" in cause) {
    const message = (cause as { message?: unknown }).message;
    if (typeof message === "string") return message;
  }
  return String(cause);
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
