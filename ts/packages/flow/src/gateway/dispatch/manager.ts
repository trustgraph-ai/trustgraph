/**
 * Dispatcher manager — routes requests to backend services via pub/sub.
 *
 * Maintains a service registry mapping service names to NATS topic pairs.
 * Applies wire format translation on requests (client → internal) and
 * reverse translation on responses (internal → client).
 *
 * Python reference: trustgraph-flow/trustgraph/gateway/dispatch/manager.py
 */

import { NatsBackend, RequestResponse, type PubSubBackend } from "@trustgraph/base";
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

export class DispatcherManager {
  private readonly pubsub: PubSubBackend;
  private requestors = new Map<string, Promise<RequestResponse<unknown, unknown>>>();

  constructor(config: GatewayConfig) {
    this.pubsub = new NatsBackend(config.natsUrl ?? "nats://localhost:4222");
  }

  async start(): Promise<void> {
    // Requestors are created on demand when first accessed
  }

  async stop(): Promise<void> {
    for (const pending of this.requestors.values()) {
      const rr = await pending;
      await rr.stop();
    }
    await this.pubsub.close();
  }

  // ---------- Internal helpers ----------

  private getRequestor(
    requestTopic: string,
    responseTopic: string,
    key: string,
  ): Promise<RequestResponse<unknown, unknown>> {
    let pending = this.requestors.get(key);
    if (!pending) {
      pending = (async () => {
        const rr = new RequestResponse({
          pubsub: this.pubsub,
          requestTopic,
          responseTopic,
          subscription: `gateway-${key}`,
        });
        await rr.start();
        return rr;
      })();
      this.requestors.set(key, pending);
    }
    return pending;
  }

  private resolveGlobalTopics(
    kind: string,
  ): { requestTopic: string; responseTopic: string } {
    const entry = GLOBAL_SERVICES.get(kind);
    if (entry) {
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
  }

  private resolveFlowTopics(
    kind: string,
  ): { requestTopic: string; responseTopic: string } {
    const entry = FLOW_SERVICES.get(kind);
    if (entry) {
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
  }

  /**
   * Determine whether a response is the final one in a streaming sequence.
   * Checks for various end-of-stream markers used by different services.
   */
  private isComplete(response: unknown): boolean {
    if (typeof response !== "object" || response === null) return true;
    const res = response as Record<string, unknown>;
    return (
      !!res.complete ||
      !!res.endOfStream ||
      !!res.endOfSession ||
      !!res.end_of_stream ||
      !!res.end_of_session ||
      !!res.end_of_dialog ||
      !!res.eos ||
      // error responses are always final
      !!res.error
    );
  }

  // ---------- Global service dispatch ----------

  async dispatchGlobalService(
    kind: string,
    request: Record<string, unknown>,
  ): Promise<unknown> {
    const { requestTopic, responseTopic } = this.resolveGlobalTopics(kind);
    const rr = await this.getRequestor(requestTopic, responseTopic, `global:${kind}`);

    const translated = translateRequest(kind, request);
    const response = await rr.request(translated);
    return translateResponse(kind, response);
  }

  async dispatchGlobalServiceStreaming(
    kind: string,
    request: Record<string, unknown>,
    responder: Responder,
  ): Promise<void> {
    const { requestTopic, responseTopic } = this.resolveGlobalTopics(kind);
    const rr = await this.getRequestor(requestTopic, responseTopic, `global:${kind}`);
    const translated = translateRequest(kind, request);

    await rr.request(translated, {
      recipient: async (response) => {
        const translatedRes = translateResponse(kind, response);
        const complete = this.isComplete(translatedRes);
        await responder(translatedRes, complete);
        return complete;
      },
    });
  }

  // ---------- Flow-scoped service dispatch ----------

  async dispatchFlowService(
    flow: string,
    kind: string,
    request: Record<string, unknown>,
  ): Promise<unknown> {
    const { requestTopic, responseTopic } = this.resolveFlowTopics(kind);
    const rr = await this.getRequestor(
      requestTopic,
      responseTopic,
      `flow:${flow}:${kind}`,
    );

    const translated = translateRequest(kind, request);
    const response = await rr.request(translated);
    return translateResponse(kind, response);
  }

  async dispatchFlowServiceStreaming(
    flow: string,
    kind: string,
    request: Record<string, unknown>,
    responder: Responder,
  ): Promise<void> {
    const { requestTopic, responseTopic } = this.resolveFlowTopics(kind);
    const rr = await this.getRequestor(
      requestTopic,
      responseTopic,
      `flow:${flow}:${kind}`,
    );
    const translated = translateRequest(kind, request);

    await rr.request(translated, {
      recipient: async (response) => {
        const translatedRes = translateResponse(kind, response);
        const complete = this.isComplete(translatedRes);
        await responder(translatedRes, complete);
        return complete;
      },
    });
  }

  // ---------- Fire-and-forget publish ----------

  /**
   * Publish a single message to an arbitrary topic (no request/response).
   * Used for injecting documents into the processing pipeline.
   */
  async publishToTopic(topic: string, message: unknown, id?: string): Promise<void> {
    const producer = await this.pubsub.createProducer<unknown>({ topic });
    const messageId = id ?? `pub-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    await producer.send(message, { id: messageId });
    await producer.close();
  }

  // ---------- Static introspection ----------

  static get flowServiceNames(): readonly string[] {
    return [...FLOW_SERVICES.keys()];
  }

  static get globalServiceNames(): readonly string[] {
    return [...GLOBAL_SERVICES.keys()];
  }

  static isStreamingService(kind: string): boolean {
    return STREAMING_SERVICES.has(kind);
  }
}
