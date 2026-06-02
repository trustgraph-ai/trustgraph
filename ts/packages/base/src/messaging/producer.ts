/**
 * High-level async producer with queue buffering and retry.
 *
 * Python reference: trustgraph-base/trustgraph/base/producer.py
 */

import type { PubSubBackend } from "../backend/types.js";
import type { ProducerMetrics } from "../metrics/index.ts";
import { Effect, Exit, Scope } from "effect";
import { PubSub } from "../backend/pubsub.js";
import { makeEffectProducerFromPubSub, type EffectProducer } from "./runtime.js";
import { messagingLifecycleError } from "../errors.js";

export interface Producer<T> {
  readonly start: () => Promise<void>;
  readonly send: (id: string, message: T) => Promise<void>;
  readonly stop: () => Promise<void>;
}

interface ProducerRuntime<T> {
  readonly scope: Scope.Closeable;
  readonly producer: EffectProducer<T>;
}

export function makeProducer<T>(
  pubsub: PubSubBackend,
  topic: string,
  metrics?: ProducerMetrics,
): Producer<T> {
  let runtime: ProducerRuntime<T> | null = null;

  return {
    start: () =>
      runtime !== null
        ? Promise.resolve()
        : Effect.runPromise(
            Effect.gen(function* () {
              const scope = yield* Scope.make();
              const startProducer = Effect.gen(function* () {
                const producer = yield* makeEffectProducerFromPubSub<T>(
                  PubSub.fromBackend(pubsub),
                  {
                    topic,
                    ...(metrics === undefined ? {} : { metrics }),
                  },
                ).pipe(
                  Scope.provide(scope),
                  Effect.mapError((error) => messagingLifecycleError(topic, "create-producer", error)),
                );

                runtime = { scope, producer };
              });

              yield* startProducer.pipe(
                Effect.onError((cause) => Scope.close(scope, Exit.failCause(cause))),
              );
            }),
          ),
    send: (id, message) => {
      const current = runtime;
      return current === null
        ? Effect.runPromise(Effect.fail(messagingLifecycleError(topic, "send", "Producer not started")))
        : Effect.runPromise(current.producer.send(id, message));
    },
    stop: () => {
      const current = runtime;
      runtime = null;
      return current === null
        ? Promise.resolve()
        : Effect.runPromise(
            current.producer.flush.pipe(
              Effect.ensuring(Scope.close(current.scope, Exit.void)),
            ),
          );
    },
  };
}
