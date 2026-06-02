/**
 * Dispatcher manager — routes requests to backend services via pub/sub.
 *
 * Maintains a service registry mapping service names to NATS topic pairs.
 * Applies wire format translation on requests (client → internal) and
 * reverse translation on responses (internal → client).
 *
 * Python reference: trustgraph-flow/trustgraph/gateway/dispatch/manager.py
 */

import { makeNatsBackend, makeRequestResponse, type PubSubBackend, type RequestResponse } from "@trustgraph/base";
import type { GatewayConfig } from "../server.js";
import { translateRequest, translateResponse } from "./serialize.js";

export type Responder = (response: unknown, complete: boolean) => Promise<void>;

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

export function makeDispatcherManager(config: GatewayConfig): DispatcherManager {
  const pubsub: PubSubBackend = makeNatsBackend(config.natsUrl ?? "nats://localhost:4222");
  const requestors = new Map<string, Promise<RequestResponse<unknown, unknown>>>();

  const start = async (): Promise<void> => {
    // Requestors are created on demand when first accessed
  };

  const stop = async (): Promise<void> => {
    for (const pending of requestors.values()) {
      const rr = await pending;
      await rr.stop();
    }
    await pubsub.close();
  };

  // ---------- Internal helpers ----------

  const getRequestor = (
    requestTopic: string,
    responseTopic: string,
    key: string,
  ): Promise<RequestResponse<unknown, unknown>> => {
    let pending = requestors.get(key);
    if (pending === undefined) {
      pending = (async () => {
        const rr = makeRequestResponse({
          pubsub,
          requestTopic,
          responseTopic,
          subscription: `gateway-${key}`,
        });
        await rr.start();
        return rr;
      })();
      requestors.set(key, pending);
    }
    return pending;
  };

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

  /**
   * Determine whether a response is the final one in a streaming sequence.
   * Checks for various end-of-stream markers used by different services.
   */
  const isComplete = (response: unknown): boolean => {
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

  // ---------- Global service dispatch ----------

  const dispatchGlobalService = async (
    kind: string,
    request: Record<string, unknown>,
  ): Promise<unknown> => {
    const { requestTopic, responseTopic } = resolveGlobalTopics(kind);
    const rr = await getRequestor(requestTopic, responseTopic, `global:${kind}`);

    const translated = translateRequest(kind, request);
    const response = await rr.request(translated);
    return translateResponse(kind, response);
  };

  const dispatchGlobalServiceStreaming = async (
    kind: string,
    request: Record<string, unknown>,
    responder: Responder,
  ): Promise<void> => {
    const { requestTopic, responseTopic } = resolveGlobalTopics(kind);
    const rr = await getRequestor(requestTopic, responseTopic, `global:${kind}`);
    const translated = translateRequest(kind, request);

    await rr.request(translated, {
      recipient: async (response) => {
        const translatedRes = translateResponse(kind, response);
        const complete = isComplete(translatedRes);
        await responder(translatedRes, complete);
        return complete;
      },
    });
  };

  // ---------- Flow-scoped service dispatch ----------

  const dispatchFlowService = async (
    flow: string,
    kind: string,
    request: Record<string, unknown>,
  ): Promise<unknown> => {
    const { requestTopic, responseTopic } = resolveFlowTopics(kind);
    const rr = await getRequestor(
      requestTopic,
      responseTopic,
      `flow:${flow}:${kind}`,
    );

    const translated = translateRequest(kind, request);
    const response = await rr.request(translated);
    return translateResponse(kind, response);
  };

  const dispatchFlowServiceStreaming = async (
    flow: string,
    kind: string,
    request: Record<string, unknown>,
    responder: Responder,
  ): Promise<void> => {
    const { requestTopic, responseTopic } = resolveFlowTopics(kind);
    const rr = await getRequestor(
      requestTopic,
      responseTopic,
      `flow:${flow}:${kind}`,
    );
    const translated = translateRequest(kind, request);

    await rr.request(translated, {
      recipient: async (response) => {
        const translatedRes = translateResponse(kind, response);
        const complete = isComplete(translatedRes);
        await responder(translatedRes, complete);
        return complete;
      },
    });
  };

  // ---------- Fire-and-forget publish ----------

  /**
   * Publish a single message to an arbitrary topic (no request/response).
   * Used for injecting documents into the processing pipeline.
   */
  const publishToTopic = async (topic: string, message: unknown, id?: string): Promise<void> => {
    const producer = await pubsub.createProducer<unknown>({ topic });
    const messageId = id ?? `pub-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    await producer.send(message, { id: messageId });
    await producer.close();
  };

  return {
    start,
    stop,
    dispatchGlobalService,
    dispatchGlobalServiceStreaming,
    dispatchFlowService,
    dispatchFlowServiceStreaming,
    publishToTopic,
  };
}
