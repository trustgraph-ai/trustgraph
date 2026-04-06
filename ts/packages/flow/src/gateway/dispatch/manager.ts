/**
 * Dispatcher manager — routes requests to backend services via pub/sub.
 *
 * Python reference: trustgraph-flow/trustgraph/gateway/dispatch/manager.py
 */

import { NatsBackend, RequestResponse, type PubSubBackend } from "@trustgraph/base";
import type { GatewayConfig } from "../server.js";

export type Responder = (response: unknown, complete: boolean) => Promise<void>;

export class DispatcherManager {
  private pubsub: PubSubBackend;
  private requestors = new Map<string, RequestResponse<unknown, unknown>>();

  constructor(private readonly config: GatewayConfig) {
    this.pubsub = new NatsBackend(config.natsUrl ?? "nats://localhost:4222");
  }

  async start(): Promise<void> {
    // Pre-create requestors for known global services
    // Flow-specific requestors are created on demand
  }

  async stop(): Promise<void> {
    for (const rr of this.requestors.values()) {
      await rr.stop();
    }
    await this.pubsub.close();
  }

  private async getRequestor(
    requestTopic: string,
    responseTopic: string,
    key: string,
  ): Promise<RequestResponse<unknown, unknown>> {
    let rr = this.requestors.get(key);
    if (!rr) {
      rr = new RequestResponse({
        pubsub: this.pubsub,
        requestTopic,
        responseTopic,
        subscription: `gateway-${key}`,
      });
      await rr.start();
      this.requestors.set(key, rr);
    }
    return rr;
  }

  async dispatchGlobalService(
    kind: string,
    request: Record<string, unknown>,
  ): Promise<unknown> {
    const requestTopic = `tg.flow.${kind}-request`;
    const responseTopic = `tg.flow.${kind}-response`;
    const rr = await this.getRequestor(requestTopic, responseTopic, `global:${kind}`);
    return rr.request(request);
  }

  async dispatchFlowService(
    flow: string,
    kind: string,
    request: Record<string, unknown>,
  ): Promise<unknown> {
    const requestTopic = `tg.flow.${kind}-request`;
    const responseTopic = `tg.flow.${kind}-response`;
    const rr = await this.getRequestor(requestTopic, responseTopic, `flow:${flow}:${kind}`);
    return rr.request(request);
  }

  async dispatchGlobalServiceStreaming(
    kind: string,
    request: Record<string, unknown>,
    responder: Responder,
  ): Promise<void> {
    const requestTopic = `tg.flow.${kind}-request`;
    const responseTopic = `tg.flow.${kind}-response`;
    const rr = await this.getRequestor(requestTopic, responseTopic, `global:${kind}`);

    await rr.request(request, {
      recipient: async (response) => {
        const res = response as Record<string, unknown>;
        const complete = !!res.complete || !!res.endOfStream || !!res.endOfSession;
        await responder(res, complete);
        return complete;
      },
    });
  }

  async dispatchFlowServiceStreaming(
    flow: string,
    kind: string,
    request: Record<string, unknown>,
    responder: Responder,
  ): Promise<void> {
    const requestTopic = `tg.flow.${kind}-request`;
    const responseTopic = `tg.flow.${kind}-response`;
    const rr = await this.getRequestor(requestTopic, responseTopic, `flow:${flow}:${kind}`);

    await rr.request(request, {
      recipient: async (response) => {
        const res = response as Record<string, unknown>;
        const complete = !!res.complete || !!res.endOfStream || !!res.endOfSession;
        await responder(res, complete);
        return complete;
      },
    });
  }
}
