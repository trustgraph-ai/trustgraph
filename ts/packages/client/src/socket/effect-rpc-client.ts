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

export class EffectRpcClient {
  private readonly url: string;
  private readonly onConnect: (() => void) | undefined;
  private readonly onDisconnect: (() => void) | undefined;
  private readonly scopePromise: Promise<Scope.Scope>;
  private readonly clientPromise: Promise<TrustGraphRpcClient>;
  private readonly listeners = new Set<(state: RpcConnectionState) => void>();
  private state: RpcConnectionState = { status: "connecting" };
  private closed = false;

  constructor(
    url: string,
    onConnect?: () => void,
    onDisconnect?: () => void,
  ) {
    this.url = url;
    this.onConnect = onConnect;
    this.onDisconnect = onDisconnect;
    this.scopePromise = Effect.runPromise(Scope.make());
    this.clientPromise = this.scopePromise.then((scope) =>
      Effect.runPromise(this.makeClient().pipe(Scope.provide(scope))),
    );
    this.clientPromise.catch((cause) => {
      this.setState({
        status: "failed",
        lastError: errorMessage(cause),
      });
    });
  }

  subscribe(listener: (state: RpcConnectionState) => void): () => void {
    this.listeners.add(listener);
    listener(this.state);
    return () => {
      this.listeners.delete(listener);
    };
  }

  async dispatch(input: DispatchInput, options: DispatchOptions = {}): Promise<unknown> {
    const client = await this.clientPromise;
    return await Effect.runPromise(
      this.withRequestPolicy(client.Dispatch(new DispatchPayload(input)), options),
    );
  }

  async dispatchStream(
    input: DispatchInput,
    receiver: (chunk: DispatchStreamChunk) => boolean,
    options: DispatchOptions = {},
  ): Promise<DispatchStreamChunk | undefined> {
    const client = await this.clientPromise;
    let last: DispatchStreamChunk | undefined;
    await Effect.runPromise(
      this.withRequestPolicy(
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
  }

  async close(): Promise<void> {
    if (this.closed) return;
    this.closed = true;
    this.setState({ status: "closed" });
    const scope = await this.scopePromise;
    await Effect.runPromise(Scope.close(scope, Exit.void));
  }

  private makeClient(): Effect.Effect<TrustGraphRpcClient, never, Scope.Scope> {
    const socketLayer = Layer.effect(
      Socket.Socket,
      Socket.makeWebSocket(this.url, {
        closeCodeIsError: (code) => code !== 1000,
        openTimeout: "10 seconds",
      }),
    ).pipe(Layer.provide(webSocketConstructorLayer));

    const hooksLayer = Layer.succeed(
      RpcClient.ConnectionHooks,
      RpcClient.ConnectionHooks.of({
        onConnect: Effect.sync(() => {
          this.setState({ status: "connected" });
          this.onConnect?.();
        }),
        onDisconnect: Effect.sync(() => {
          if (!this.closed) {
            this.setState({
              status: "connecting",
              lastError: "Disconnected from gateway",
            });
          }
          this.onDisconnect?.();
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
  }

  private setState(state: RpcConnectionState): void {
    this.state = state;
    for (const listener of this.listeners) {
      listener(state);
    }
  }

  private withRequestPolicy<A, E, R>(
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
