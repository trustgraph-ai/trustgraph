/**
 * High-level async producer with queue buffering and retry.
 *
 * Python reference: trustgraph-base/trustgraph/base/producer.py
 */

import type { PubSubBackend } from "../backend/types.js";
import type { ProducerMetrics } from "../metrics/prometheus.js";
import { Effect } from "effect";
import { makeEffectProducerHandle, type EffectProducer } from "./runtime.js";
import { messagingLifecycleError } from "../errors.js";

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
    start: () =>
      Effect.runPromise(
        Effect.gen(function* () {
          const backend = yield* Effect.tryPromise({
            try: () => pubsub.createProducer<T>({ topic }),
            catch: (error) => messagingLifecycleError(topic, "create-producer", error),
          });
          effectProducer = makeEffectProducerHandle(backend, {
            topic,
            ...(metrics === undefined ? {} : { metrics }),
          });
        }),
      ),
    send: (id, message) =>
      effectProducer === null
        ? Effect.runPromise(Effect.fail(messagingLifecycleError(topic, "send", "Producer not started")))
        : Effect.runPromise(effectProducer.send(id, message)),
    stop: () =>
      Effect.runPromise(
        Effect.gen(function* () {
          if (effectProducer !== null) {
            const producer = effectProducer;
            yield* producer.flush.pipe(
              Effect.flatMap(() => producer.close),
              Effect.ensuring(
                Effect.sync(() => {
                  effectProducer = null;
                }),
              ),
            );
          }
        }),
      ),
  };
}
