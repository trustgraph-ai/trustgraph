/**
 * Request/response pattern over pub/sub.
 *
 * Sends a request with a unique ID, subscribes for matching responses.
 * Supports streaming (multiple responses per request) via a recipient callback.
 *
 * Python reference: trustgraph-base/trustgraph/base/request_response_spec.py
 */

import { randomUUID } from "node:crypto";
import { makeProducer, type Producer } from "./producer.js";
import { makeSubscriber, type Subscriber } from "./subscriber.js";
import type { PubSubBackend } from "../backend/types.js";

export interface RequestResponseOptions {
  pubsub: PubSubBackend;
  requestTopic: string;
  responseTopic: string;
  subscription: string;
}

export interface RequestResponse<TReq, TRes> {
  readonly start: () => Promise<void>;
  readonly stop: () => Promise<void>;
  readonly request: (
    request: TReq,
    options?: {
      timeoutMs?: number;
      recipient?: (response: TRes) => Promise<boolean>;
    },
  ) => Promise<TRes>;
}

export function makeRequestResponse<TReq, TRes>(
  options: RequestResponseOptions,
): RequestResponse<TReq, TRes> {
  const producer: Producer<TReq> = makeProducer<TReq>(options.pubsub, options.requestTopic);
  const subscriber: Subscriber<TRes> = makeSubscriber<TRes>(
    options.pubsub,
    options.responseTopic,
    options.subscription,
  );

  return {
    start: async () => {
      await producer.start();
      await subscriber.start();
    },
    stop: async () => {
      await producer.stop();
      await subscriber.stop();
    },
    /**
     * Send a request and wait for responses.
     *
     * @param request - The request payload
     * @param options.timeoutMs - Total timeout in milliseconds (default: 300s)
     * @param options.recipient - Optional callback for streaming responses.
     *   Return `true` to indicate the final response has been received.
     *   If omitted, returns the first response.
     */
    request: async (request, requestOptions) => {
      const id = randomUUID();
      const timeoutMs = requestOptions?.timeoutMs ?? 300_000;
      const recipient = requestOptions?.recipient;

      const queue = subscriber.subscribe(id);

      try {
        await producer.send(id, request);

        const deadline = Date.now() + timeoutMs;

        while (true) {
          const remaining = deadline - Date.now();
          if (remaining <= 0) {
            throw new Error(`Request timed out after ${timeoutMs}ms`);
          }

          const response = await queue.pop(remaining);

          if (recipient !== undefined) {
            const isFinal = await recipient(response);
            if (isFinal) return response;
          } else {
            return response;
          }
        }
      } finally {
        subscriber.unsubscribe(id);
      }
    },
  };
}
