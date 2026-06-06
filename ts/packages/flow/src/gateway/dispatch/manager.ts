/**
 * Dispatcher manager — routes requests to backend services via pub/sub.
 *
 * Maintains a service registry mapping service names to NATS topic pairs.
 * Applies wire format translation on requests (client → internal) and
 * reverse translation on responses (internal → client).
 *
 * Python reference: trustgraph-flow/trustgraph/gateway/dispatch/manager.py
 */

import { Clock, Effect, Exit, HashMap, HashSet, Option, Random, Scope, SynchronizedRef, Tuple } from "effect";
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
interface ServiceTopics {
  readonly request: string;
  readonly response: string;
}

const FLOW_SERVICE_ENTRIES: ReadonlyArray<readonly [string, ServiceTopics]> = [
  ["agent", { request: "agent-request", response: "agent-response" }],
  ["text-completion", { request: "text-completion-request", response: "text-completion-response" }],
  ["prompt", { request: "prompt-request", response: "prompt-response" }],
  ["graph-rag", { request: "graph-rag-request", response: "graph-rag-response" }],
  ["document-rag", { request: "document-rag-request", response: "document-rag-response" }],
  ["embeddings", { request: "embeddings-request", response: "embeddings-response" }],
  ["graph-embeddings", { request: "graph-embeddings-request", response: "graph-embeddings-response" }],
  ["document-embeddings", { request: "doc-embeddings-request", response: "doc-embeddings-response" }],
  ["triples", { request: "triples-request", response: "triples-response" }],
  ["mcp-tool", { request: "mcp-tool-request", response: "mcp-tool-response" }],
];

const FLOW_SERVICES: HashMap.HashMap<string, ServiceTopics> = HashMap.fromIterable(FLOW_SERVICE_ENTRIES);

/**
 * Global services (not flow-scoped).
 * These always use fixed topics regardless of which flow is active.
 */
const GLOBAL_SERVICE_ENTRIES: ReadonlyArray<readonly [string, ServiceTopics]> = [
  ["config", { request: "config-request", response: "config-response" }],
  ["flow", { request: "flow-request", response: "flow-response" }],
  ["librarian", { request: "librarian-request", response: "librarian-response" }],
  ["knowledge", { request: "knowledge-request", response: "knowledge-response" }],
  ["collection-management", { request: "collection-management-request", response: "collection-management-response" }],
];

const GLOBAL_SERVICES: HashMap.HashMap<string, ServiceTopics> = HashMap.fromIterable(GLOBAL_SERVICE_ENTRIES);

/**
 * Services that support streaming responses (multiple messages per request).
 * The completion flag is determined by checking for end-of-stream markers.
 */
const STREAMING_SERVICES = HashSet.make(
  "agent",
  "text-completion",
  "graph-rag",
  "document-rag",
  "triples",
  "knowledge",
  "librarian",
);

function topicName(name: string): string {
  return `tg.flow.${name}`;
}

// ---------- Manager ----------

export interface DispatcherManager {
  readonly start: Effect.Effect<void, MessagingLifecycleError>;
  readonly stop: Effect.Effect<void, MessagingLifecycleError>;
  readonly dispatchGlobalService: (
    kind: string,
    request: Record<string, unknown>,
  ) => Effect.Effect<unknown, DispatcherStreamError>;
  readonly dispatchGlobalServiceStreaming: <E = never, R = never>(
    kind: string,
    request: Record<string, unknown>,
    responder: EffectResponder<E, R>,
  ) => Effect.Effect<void, DispatcherStreamError<E>, R>;
  readonly dispatchFlowService: (
    flow: string,
    kind: string,
    request: Record<string, unknown>,
  ) => Effect.Effect<unknown, DispatcherStreamError>;
  readonly dispatchFlowServiceStreaming: <E = never, R = never>(
    flow: string,
    kind: string,
    request: Record<string, unknown>,
    responder: EffectResponder<E, R>,
  ) => Effect.Effect<void, DispatcherStreamError<E>, R>;
  readonly publishToTopic: (
    topic: string,
    message: unknown,
    id?: string,
  ) => Effect.Effect<void, MessagingDeliveryError>;
}

export const dispatcherManagerFlowServiceNames = (): readonly string[] => [
  ...FLOW_SERVICE_ENTRIES.map(([name]) => name),
];

export const dispatcherManagerGlobalServiceNames = (): readonly string[] => [
  ...GLOBAL_SERVICE_ENTRIES.map(([name]) => name),
];

export const dispatcherManagerIsStreamingService = (kind: string): boolean =>
  HashSet.has(STREAMING_SERVICES, kind);

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

type RequestorMap = HashMap.HashMap<string, EffectRequestResponse<unknown, unknown>>;

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
      const requestors = yield* SynchronizedRef.make(
        HashMap.empty<string, EffectRequestResponse<unknown, unknown>>(),
      );
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

  const stopEffect = Effect.fn("DispatcherManager.stop")(function* () {
    const current = runtime;
    runtime = null;

    if (current !== null) {
      yield* Scope.close(current.scope, Exit.void);
    }

    if (ownsPubSub) {
      yield* pubsub.close.pipe(
        Effect.mapError((cause) => messagingLifecycleError("gateway-dispatcher", "close-pubsub", cause)),
      );
    }
  });

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

    return yield* SynchronizedRef.modifyEffect(current.requestors, (requestors) =>
      Option.match(HashMap.get(requestors, key), {
        onNone: () =>
          current.factory.make<unknown, unknown>({
            requestTopic,
            responseTopic,
            subscription: `gateway-${key}`,
          }).pipe(
            Scope.provide(current.scope),
            Effect.map((requestor) => Tuple.make(requestor, HashMap.set(requestors, key, requestor))),
          ),
        onSome: (cached) => Effect.succeed(Tuple.make(cached, requestors)),
      })
    );
  });

  const resolveGlobalTopics = (
    kind: string,
  ): { requestTopic: string; responseTopic: string } =>
    Option.match(HashMap.get(GLOBAL_SERVICES, kind), {
      onNone: () => ({
        requestTopic: topicName(`${kind}-request`),
        responseTopic: topicName(`${kind}-response`),
      }),
      onSome: (entry) => ({
        requestTopic: topicName(entry.request),
        responseTopic: topicName(entry.response),
      }),
    });

  const resolveFlowTopics = (
    kind: string,
  ): { requestTopic: string; responseTopic: string } =>
    Option.match(HashMap.get(FLOW_SERVICES, kind), {
      onNone: () => ({
        requestTopic: topicName(`${kind}-request`),
        responseTopic: topicName(`${kind}-response`),
      }),
      onSome: (entry) => ({
        requestTopic: topicName(entry.request),
        responseTopic: topicName(entry.response),
      }),
    });

  // ---------- Global service dispatch ----------

  const dispatchGlobalService = Effect.fn("DispatcherManager.dispatchGlobalService")(function* (
    kind: string,
    request: Record<string, unknown>,
  ) {
    const { requestTopic, responseTopic } = resolveGlobalTopics(kind);
    const translated = yield* translateRequestEffect(kind, request);
    const rr = yield* getRequestorEffect(requestTopic, responseTopic, `global:${kind}`);

    const response = yield* rr.request(translated);
    return yield* translateResponseEffect(kind, response);
  });

  const dispatchGlobalServiceStreaming = Effect.fn("DispatcherManager.dispatchGlobalServiceStreaming")(function* <
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

  // ---------- Flow-scoped service dispatch ----------

  const dispatchFlowService = Effect.fn("DispatcherManager.dispatchFlowService")(function* (
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

  const dispatchFlowServiceStreaming = Effect.fn("DispatcherManager.dispatchFlowServiceStreaming")(function* <
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

  // ---------- Fire-and-forget publish ----------

  /**
   * Publish a single message to an arbitrary topic (no request/response).
   * Used for injecting documents into the processing pipeline.
   */
  const publishToTopic = (topic: string, message: unknown, id?: string) =>
    Effect.acquireUseRelease(
      pubsub.createProducer<unknown>({ topic }).pipe(
        Effect.mapError((cause) => messagingDeliveryError(topic, "create-producer", cause)),
      ),
      (producer) =>
        Effect.gen(function* () {
          const timestamp = yield* Clock.currentTimeMillis;
          const suffix = yield* Random.nextIntBetween(0, 36 ** 6, { halfOpen: true });
          const messageId = id ?? `pub-${timestamp}-${suffix.toString(36).padStart(6, "0")}`;

          yield* producer.send(message, { id: messageId }).pipe(
            Effect.mapError((cause) => messagingDeliveryError(topic, "send", cause)),
          );
        }),
      (producer) =>
        producer.close.pipe(
          Effect.mapError((cause) => messagingDeliveryError(topic, "close-producer", cause)),
        ),
    );

  return {
    start: startEffect(),
    stop: stopEffect(),
    dispatchGlobalService,
    dispatchGlobalServiceStreaming,
    dispatchFlowService,
    dispatchFlowServiceStreaming,
    publishToTopic,
  };
}
