/**
 * High-level async producer with queue buffering and retry.
 *
 * Python reference: trustgraph-base/trustgraph/base/producer.py
 */

import type { PubSubBackend } from "../backend/types.js";
import type { ProducerMetrics } from "../metrics/prometheus.js";
import { Effect } from "effect";
import { makeEffectProducerHandle, type EffectProducer } from "./runtime.js";

export interface Producer<T> {
  readonly start: () => Promise<void>;
  readonly send: (id: string, message: T) => Promise<void>;
  readonly stop: () => Promise<void>;
}

export function makeProducer<T>(
  pubsub: PubSubBackend,
  topic: string,
  metrics?: ProducerMetrics,
): Producer<T> {
  let effectProducer: EffectProducer<T> | null = null;

  return {
    start: async () => {
      const backend = await pubsub.createProducer<T>({ topic });
      effectProducer = makeEffectProducerHandle(backend, {
        topic,
        ...(metrics === undefined ? {} : { metrics }),
      });
    },
    send: async (id, message) => {
      if (effectProducer === null) throw new Error("Producer not started");

      await Effect.runPromise(effectProducer.send(id, message));
    },
    stop: async () => {
      if (effectProducer !== null) {
        const producer = effectProducer;
        await Effect.runPromise(
          producer.flush.pipe(
            Effect.flatMap(() => producer.close),
          ),
        );
        effectProducer = null;
      }
    },
  };
}
