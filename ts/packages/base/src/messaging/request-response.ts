/**
 * Request/response pattern over pub/sub.
 *
 * Sends a request with a unique ID, subscribes for matching responses.
 * Supports streaming (multiple responses per request) via a recipient callback.
 *
 * Python reference: trustgraph-base/trustgraph/base/request_response_spec.py
 */

import { randomUUID } from "node:crypto";
import { Producer } from "./producer.js";
import { Subscriber } from "./subscriber.js";
import type { PubSubBackend } from "../backend/types.js";

export interface RequestResponseOptions {
  pubsub: PubSubBackend;
  requestTopic: string;
  responseTopic: string;
  subscription: string;
}

export class RequestResponse<TReq, TRes> {
  private producer: Producer<TReq>;
  private subscriber: Subscriber<TRes>;

  constructor(private readonly options: RequestResponseOptions) {
    this.producer = new Producer<TReq>(options.pubsub, options.requestTopic);
    this.subscriber = new Subscriber<TRes>(
      options.pubsub,
      options.responseTopic,
      options.subscription,
    );
  }

  async start(): Promise<void> {
    await this.producer.start();
    await this.subscriber.start();
  }

  async stop(): Promise<void> {
    await this.producer.stop();
    await this.subscriber.stop();
  }

  /**
   * Send a request and wait for responses.
   *
   * @param request - The request payload
   * @param options.timeoutMs - Total timeout in milliseconds (default: 300s)
   * @param options.recipient - Optional callback for streaming responses.
   *   Return `true` to indicate the final response has been received.
   *   If omitted, returns the first response.
   */
  async request(
    request: TReq,
    options?: {
      timeoutMs?: number;
      recipient?: (response: TRes) => Promise<boolean>;
    },
  ): Promise<TRes> {
    const id = randomUUID();
    const timeoutMs = options?.timeoutMs ?? 300_000;
    const recipient = options?.recipient;

    const queue = this.subscriber.subscribe(id);

    try {
      await this.producer.send(id, request);

      const deadline = Date.now() + timeoutMs;

      while (true) {
        const remaining = deadline - Date.now();
        if (remaining <= 0) {
          throw new Error(`Request timed out after ${timeoutMs}ms`);
        }

        const response = await queue.pop(remaining);

        if (recipient) {
          const isFinal = await recipient(response);
          if (isFinal) return response;
        } else {
          return response;
        }
      }
    } finally {
      this.subscriber.unsubscribe(id);
    }
  }
}
