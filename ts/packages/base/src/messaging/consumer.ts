/**
 * High-level consumer with concurrency, retry, and rate-limit handling.
 *
 * Python reference: trustgraph-base/trustgraph/base/consumer.py
 */

import type { PubSubBackend, BackendConsumer, Message } from "../backend/types.js";
import type { Flow } from "../processor/flow.js";
import { TooManyRequestsError } from "../errors.js";
import * as S from "effect/Schema";

export type MessageHandler<T> = (
  message: T,
  properties: Record<string, string>,
  flow: FlowContext,
) => Promise<void>;

export interface FlowContext<Requirements = never> {
  id: string;
  name: string;
  /** Reference to the owning Flow instance, giving handlers access to producers and parameters. */
  flow: Flow<Requirements>;
}

export interface ConsumerOptions<T> {
  pubsub: PubSubBackend;
  topic: string;
  subscription: string;
  handler: MessageHandler<T>;
  concurrency?: number;
  initialPosition?: "latest" | "earliest";
  rateLimitRetryMs?: number;
  rateLimitTimeoutMs?: number;
}

declare const ConsumerMessageType: unique symbol;

export interface Consumer<T> {
  readonly [ConsumerMessageType]?: (_: T) => T;
  readonly start: (flow: FlowContext) => Promise<void>;
  readonly stop: () => Promise<void>;
}

export function makeConsumer<T>(options: ConsumerOptions<T>): Consumer<T> {
  let backend: BackendConsumer<T> | null = null;
  let running = false;
  let abortController = new AbortController();
  const concurrency = options.concurrency ?? 1;
  const rateLimitRetryMs = options.rateLimitRetryMs ?? 10_000;

  const handleWithRetry = async (msg: Message<T>, flow: FlowContext): Promise<void> => {
    try {
      await options.handler(msg.value(), msg.properties(), flow);
    } catch (err) {
      if (S.is(TooManyRequestsError)(err)) {
        console.warn(`[Consumer] Rate limited, retrying in ${rateLimitRetryMs}ms`);
        await sleep(rateLimitRetryMs);
        await options.handler(msg.value(), msg.properties(), flow);
      } else {
        throw err;
      }
    }
  };

  const consumeLoop = async (flow: FlowContext): Promise<void> => {
    while (running) {
      let msg: Message<T> | null = null;
      try {
        const currentBackend = backend;
        if (currentBackend === null) throw new Error("Consumer backend not started");

        msg = await currentBackend.receive(2000);
        if (msg === null) continue;

        await handleWithRetry(msg, flow);
        await currentBackend.acknowledge(msg);
      } catch (err) {
        if (!running) break;
        console.error("[Consumer] Error in consume loop:", err);
        if (msg !== null) {
          try {
            const currentBackend = backend;
            if (currentBackend !== null) {
              await currentBackend.negativeAcknowledge(msg);
            }
          } catch (nakErr) {
            console.error("[Consumer] Failed to nak message:", nakErr);
          }
        }
        await sleep(1000);
      }
    }
  };

  return {
    start: async (flow) => {
      backend = await options.pubsub.createConsumer<T>({
        topic: options.topic,
        subscription: options.subscription,
        initialPosition: options.initialPosition ?? "latest",
      });

      running = true;

      // Spawn concurrent consumer tasks.
      const tasks = Array.from({ length: concurrency }, () =>
        consumeLoop(flow),
      );
      // Run all concurrently: first rejection stops all.
      await Promise.all(tasks);
    },
    stop: async () => {
      running = false;
      abortController.abort();
      abortController = new AbortController();
      if (backend !== null) {
        await backend.close();
        backend = null;
      }
    },
  };
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
