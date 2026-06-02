/**
 * Dispatcher manager — routes requests to backend services via pub/sub.
 *
 * Maintains a service registry mapping service names to NATS topic pairs.
 * Applies wire format translation on requests (client → internal) and
 * reverse translation on responses (internal → client).
 *
 * Python reference: trustgraph-flow/trustgraph/gateway/dispatch/manager.py
 */

import { Clock, Effect, Exit, Random, Scope, SynchronizedRef } from "effect";
import {
  loadMessagingRuntimeConfig,
  makeNatsBackend,
  makePubSubService,
  makeRequestResponseFactoryService,
  messagingDeliveryError,
  messagingLifecycleError,
  type EffectRequestResponse,
  type MessagingDeliveryError,
  type MessagingLifecycleError,
  type MessagingTimeoutError,
  type PubSubBackend,
  type PubSubError,
  type RequestResponseFactoryService,
} from "@trustgraph/base";
import type { GatewayConfig } from "../server.js";
import {
  translateRequestEffect,
  translateResponseEffect,
  type DispatchSerializationError,
} from "./serialize.js";

export type Responder = (response: unknown, complete: boolean) => Promise<void>;
export type EffectResponder<E = never, R = never> = (
  response: unknown,
  complete: boolean,
) => Effect.Effect<void, E, R>;
export type DispatcherStreamError<E = never> =
  | PubSubError
  | MessagingLifecycleError
  | MessagingDeliveryError
  | MessagingTimeoutError
  | DispatchSerializationError
  | E;

// ---------- Service registry ----------

/**
 * Flow-scoped request/response services.
 * These are resolved within a specific flow's interface definitions.
 * Topic pattern: tg.flow.<name>-request / tg.flow.<name>-response
 */
const FLOW_SERVICES: ReadonlyMap<string, { request: string; response: string }> = new Map([
  ["agent",               { request: "agent-request",               response: "agent-response" }],
  ["text-completion",     { request: "text-completion-request",     response: "text-completion-response" }],
  ["prompt",              { request: "prompt-request",              response: "prompt-response" }],
  ["graph-rag",           { request: "graph-rag-request",           response: "graph-rag-response" }],
  ["document-rag",        { request: "document-rag-request",        response: "document-rag-response" }],
  ["embeddings",          { request: "embeddings-request",          response: "embeddings-response" }],
  ["graph-embeddings",    { request: "graph-embeddings-request",    response: "graph-embeddings-response" }],
  ["document-embeddings", { request: "doc-embeddings-request",      response: "doc-embeddings-response" }],
  ["triples",             { request: "triples-request",             response: "triples-response" }],
  ["mcp-tool",            { request: "mcp-tool-request",            response: "mcp-tool-response" }],
]);

/**
 * Global services (not flow-scoped).
 * These always use fixed topics regardless of which flow is active.
 */
const GLOBAL_SERVICES: ReadonlyMap<string, { request: string; response: string }> = new Map([
  ["config",                  { request: "config-request",                  response: "config-response" }],
  ["flow",                    { request: "flow-request",                    response: "flow-response" }],
  ["librarian",               { request: "librarian-request",               response: "librarian-response" }],
  ["knowledge",               { request: "knowledge-request",               response: "knowledge-response" }],
  ["collection-management",   { request: "collection-management-request",   response: "collection-management-response" }],
]);

/**
 * Services that support streaming responses (multiple messages per request).
 * The completion flag is determined by checking for end-of-stream markers.
 */
const STREAMING_SERVICES = new Set([
  "agent",
  "text-completion",
  "graph-rag",
  "document-rag",
  "triples",
  "knowledge",
  "librarian",
]);

function topicName(name: string): string {
  return `tg.flow.${name}`;
}

// ---------- Manager ----------

export interface DispatcherManager {
  readonly start: () => Promise<void>;
  readonly stop: () => Promise<void>;
  readonly dispatchGlobalService: (
    kind: string,
    request: Record<string, unknown>,
  ) => Promise<unknown>;
  readonly dispatchGlobalServiceStreaming: (
    kind: string,
    request: Record<string, unknown>,
    responder: Responder,
  ) => Promise<void>;
  readonly dispatchGlobalServiceStreamingEffect: <E = never, R = never>(
    kind: string,
    request: Record<string, unknown>,
    responder: EffectResponder<E, R>,
  ) => Effect.Effect<void, DispatcherStreamError<E>, R>;
  readonly dispatchFlowService: (
    flow: string,
    kind: string,
    request: Record<string, unknown>,
  ) => Promise<unknown>;
  readonly dispatchFlowServiceStreaming: (
    flow: string,
    kind: string,
    request: Record<string, unknown>,
    responder: Responder,
  ) => Promise<void>;
  readonly dispatchFlowServiceStreamingEffect: <E = never, R = never>(
    flow: string,
    kind: string,
    request: Record<string, unknown>,
    responder: EffectResponder<E, R>,
  ) => Effect.Effect<void, DispatcherStreamError<E>, R>;
  readonly publishToTopic: (
    topic: string,
    message: unknown,
    id?: string,
  ) => Promise<void>;
}

export const dispatcherManagerFlowServiceNames = (): readonly string[] => [
  ...FLOW_SERVICES.keys(),
];

export const dispatcherManagerGlobalServiceNames = (): readonly string[] => [
  ...GLOBAL_SERVICES.keys(),
];

export const dispatcherManagerIsStreamingService = (kind: string): boolean =>
  STREAMING_SERVICES.has(kind);

export const dispatcherManagerIsCompleteResponse = (response: unknown): boolean => {
  if (typeof response !== "object" || response === null) return true;
  const res = response as Record<string, unknown>;
  return (
    res.complete === true ||
    res.endOfStream === true ||
    res.endOfSession === true ||
    res.end_of_stream === true ||
    res.end_of_session === true ||
    res.end_of_dialog === true ||
    res.eos === true ||
    // error responses are always final
    (res.error !== undefined && res.error !== null)
  );
};

type RequestorMap = Map<string, EffectRequestResponse<unknown, unknown>>;

interface DispatcherRuntime {
  readonly scope: Scope.Closeable;
  readonly requestors: SynchronizedRef.SynchronizedRef<RequestorMap>;
  readonly factory: RequestResponseFactoryService;
}

export function makeDispatcherManager(config: GatewayConfig): DispatcherManager {
  const pubsub: PubSubBackend = config.pubsub ?? makeNatsBackend(config.natsUrl ?? "nats://localhost:4222");
  const ownsPubSub = config.pubsub === undefined;
  let runtime: DispatcherRuntime | null = null;

  const startEffect = Effect.fn("DispatcherManager.start")(function* () {
    if (runtime !== null) return;

    const scope = yield* Scope.make();
    const nextRuntime = yield* Effect.gen(function* () {
      const messagingConfig = yield* loadMessagingRuntimeConfig().pipe(
        Effect.mapError((cause) =>
          messagingLifecycleError(
            "gateway-dispatcher",
            "load-messaging-config",
            cause,
          )
        ),
      );
      const requestors = yield* SynchronizedRef.make<RequestorMap>(new Map());
      return {
        scope,
        requestors,
        factory: makeRequestResponseFactoryService(makePubSubService(pubsub), messagingConfig),
      } satisfies DispatcherRuntime;
    }).pipe(
      Effect.onError((cause) => Scope.close(scope, Exit.failCause(cause))),
    );
    runtime = nextRuntime;
  });

  const start = (): Promise<void> => Effect.runPromise(startEffect());

  const stopEffect = Effect.fn("DispatcherManager.stop")(function* () {
    const current = runtime;
    runtime = null;

    if (current !== null) {
      yield* Scope.close(current.scope, Exit.void);
    }

    if (ownsPubSub) {
      yield* Effect.tryPromise({
        try: () => pubsub.close(),
        catch: (cause) => messagingLifecycleError("gateway-dispatcher", "close-pubsub", cause),
      });
    }
  });

  const stop = (): Promise<void> => Effect.runPromise(stopEffect());

  // ---------- Internal helpers ----------

  const ensureRuntimeEffect = Effect.fn("DispatcherManager.ensureRuntime")(function* () {
    if (runtime === null) {
      yield* startEffect();
    }
    if (runtime === null) {
      return yield* messagingLifecycleError(
        "gateway-dispatcher",
        "start",
        "Dispatcher manager failed to start",
      );
    }
    return runtime;
  });

  const getRequestorEffect = Effect.fn("DispatcherManager.getRequestor")(function* (
    requestTopic: string,
    responseTopic: string,
    key: string,
  ) {
    const current = yield* ensureRuntimeEffect();

    return yield* SynchronizedRef.modifyEffect(current.requestors, (requestors) => {
      const cached = requestors.get(key);
      if (cached !== undefined) {
        return Effect.succeed([cached, requestors] as const);
      }

      return current.factory.make<unknown, unknown>({
        requestTopic,
        responseTopic,
        subscription: `gateway-${key}`,
      }).pipe(
        Scope.provide(current.scope),
        Effect.map((requestor) => {
          const next = new Map(requestors);
          next.set(key, requestor);
          return [requestor, next] as const;
        }),
      );
    });
  });

  const resolveGlobalTopics = (
    kind: string,
  ): { requestTopic: string; responseTopic: string } => {
    const entry = GLOBAL_SERVICES.get(kind);
    if (entry !== undefined) {
      return {
        requestTopic: topicName(entry.request),
        responseTopic: topicName(entry.response),
      };
    }
    // Fallback: derive from kind name directly
    return {
      requestTopic: topicName(`${kind}-request`),
      responseTopic: topicName(`${kind}-response`),
    };
  };

  const resolveFlowTopics = (
    kind: string,
  ): { requestTopic: string; responseTopic: string } => {
    const entry = FLOW_SERVICES.get(kind);
    if (entry !== undefined) {
      return {
        requestTopic: topicName(entry.request),
        responseTopic: topicName(entry.response),
      };
    }
    // Fallback: derive from kind name directly
    return {
      requestTopic: topicName(`${kind}-request`),
      responseTopic: topicName(`${kind}-response`),
    };
  };

  // ---------- Global service dispatch ----------

  const dispatchGlobalService = (
    kind: string,
    request: Record<string, unknown>,
  ): Promise<unknown> =>
    Effect.runPromise(dispatchGlobalServiceEffect(kind, request));

  const dispatchGlobalServiceEffect = Effect.fn("DispatcherManager.dispatchGlobalService")(function* (
    kind: string,
    request: Record<string, unknown>,
  ) {
    const { requestTopic, responseTopic } = resolveGlobalTopics(kind);
    const translated = yield* translateRequestEffect(kind, request);
    const rr = yield* getRequestorEffect(requestTopic, responseTopic, `global:${kind}`);

    const response = yield* rr.request(translated);
    return yield* translateResponseEffect(kind, response);
  });

  const dispatchGlobalServiceStreamingEffect = Effect.fn("DispatcherManager.dispatchGlobalServiceStreaming")(function* <
    E,
    R,
  >(
    kind: string,
    request: Record<string, unknown>,
    responder: EffectResponder<E, R>,
  ) {
    const { requestTopic, responseTopic } = resolveGlobalTopics(kind);
    const translated = yield* translateRequestEffect(kind, request);
    const rr = yield* getRequestorEffect(requestTopic, responseTopic, `global:${kind}`);

    yield* rr.request(translated, {
      recipient: Effect.fn("DispatcherManager.dispatchGlobalServiceStreaming.recipient")(function* (response) {
        const translatedRes = yield* translateResponseEffect(kind, response);
        const complete = dispatcherManagerIsCompleteResponse(translatedRes);
        return yield* responder(translatedRes, complete).pipe(Effect.as(complete));
      }),
    });
  });

  const dispatchGlobalServiceStreaming = (
    kind: string,
    request: Record<string, unknown>,
    responder: Responder,
  ): Promise<void> =>
    Effect.runPromise(
      dispatchGlobalServiceStreamingEffect(kind, request, (response, complete) =>
        Effect.tryPromise({
          try: () => responder(response, complete),
          catch: (error) => messagingDeliveryError(
            resolveGlobalTopics(kind).responseTopic,
            "stream-responder",
            error,
          ),
        })
      ),
    );

  // ---------- Flow-scoped service dispatch ----------

  const dispatchFlowService = (
    flow: string,
    kind: string,
    request: Record<string, unknown>,
  ): Promise<unknown> =>
    Effect.runPromise(dispatchFlowServiceEffect(flow, kind, request));

  const dispatchFlowServiceEffect = Effect.fn("DispatcherManager.dispatchFlowService")(function* (
    flow: string,
    kind: string,
    request: Record<string, unknown>,
  ) {
    const { requestTopic, responseTopic } = resolveFlowTopics(kind);
    const translated = yield* translateRequestEffect(kind, request);
    const rr = yield* getRequestorEffect(
      requestTopic,
      responseTopic,
      `flow:${flow}:${kind}`,
    );

    const response = yield* rr.request(translated);
    return yield* translateResponseEffect(kind, response);
  });

  const dispatchFlowServiceStreamingEffect = Effect.fn("DispatcherManager.dispatchFlowServiceStreaming")(function* <
    E,
    R,
  >(
    flow: string,
    kind: string,
    request: Record<string, unknown>,
    responder: EffectResponder<E, R>,
  ) {
    const { requestTopic, responseTopic } = resolveFlowTopics(kind);
    const translated = yield* translateRequestEffect(kind, request);
    const rr = yield* getRequestorEffect(
      requestTopic,
      responseTopic,
      `flow:${flow}:${kind}`,
    );

    yield* rr.request(translated, {
      recipient: Effect.fn("DispatcherManager.dispatchFlowServiceStreaming.recipient")(function* (response) {
        const translatedRes = yield* translateResponseEffect(kind, response);
        const complete = dispatcherManagerIsCompleteResponse(translatedRes);
        return yield* responder(translatedRes, complete).pipe(Effect.as(complete));
      }),
    });
  });

  const dispatchFlowServiceStreaming = (
    flow: string,
    kind: string,
    request: Record<string, unknown>,
    responder: Responder,
  ): Promise<void> =>
    Effect.runPromise(
      dispatchFlowServiceStreamingEffect(flow, kind, request, (response, complete) =>
        Effect.tryPromise({
          try: () => responder(response, complete),
          catch: (error) => messagingDeliveryError(
            resolveFlowTopics(kind).responseTopic,
            "stream-responder",
            error,
          ),
        })
      ),
    );

  // ---------- Fire-and-forget publish ----------

  /**
   * Publish a single message to an arbitrary topic (no request/response).
   * Used for injecting documents into the processing pipeline.
   */
  const publishToTopic = (topic: string, message: unknown, id?: string): Promise<void> =>
    Effect.runPromise(
      Effect.acquireUseRelease(
        Effect.tryPromise({
          try: () => pubsub.createProducer<unknown>({ topic }),
          catch: (cause) => messagingDeliveryError(topic, "create-producer", cause),
        }),
        (producer) =>
          Effect.gen(function* () {
            const timestamp = yield* Clock.currentTimeMillis;
            const suffix = yield* Random.nextIntBetween(0, 36 ** 6, { halfOpen: true });
            const messageId = id ?? `pub-${timestamp}-${suffix.toString(36).padStart(6, "0")}`;

            yield* Effect.tryPromise({
              try: () => producer.send(message, { id: messageId }),
              catch: (cause) => messagingDeliveryError(topic, "send", cause),
            });
          }),
        (producer) => Effect.tryPromise({
          try: () => producer.close(),
          catch: (cause) => messagingDeliveryError(topic, "close-producer", cause),
        }),
      ),
    );

  return {
    start,
    stop,
    dispatchGlobalService,
    dispatchGlobalServiceStreaming,
    dispatchGlobalServiceStreamingEffect,
    dispatchFlowService,
    dispatchFlowServiceStreaming,
    dispatchFlowServiceStreamingEffect,
    publishToTopic,
  };
}
