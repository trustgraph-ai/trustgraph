/**
 * High-level async producer with queue buffering and retry.
 *
 * Python reference: trustgraph-base/trustgraph/base/producer.py
 */

import type { PubSubBackend } from "../backend/types.js";
import type { ProducerMetrics } from "../metrics/index.ts";
import { Effect, Exit, Scope } from "effect";
import { PubSub } from "../backend/pubsub.js";
import type { EffectProducer } from "./runtime.js";
import { makeEffectProducerFromPubSub, } from "./runtime.js";
import type {
  MessagingDeliveryError,
  MessagingLifecycleError,
} from "../errors.js";
import {
  messagingLifecycleError,
} from "../errors.js";

export interface Producer<T> {
  readonly start: Effect.Effect<void, MessagingLifecycleError>;
  readonly send: (id: string, message: T) => Effect.Effect<void, MessagingDeliveryError | MessagingLifecycleError>;
  readonly stop: Effect.Effect<void, MessagingDeliveryError>;
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

  const start = Effect.fn(`Producer.start:${topic}`)(function* () {
    if (runtime !== null) return;

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
  });

  return {
    start: start(),
    send: (id, message) => {
      const current = runtime;
      return current === null
        ? Effect.fail(messagingLifecycleError(topic, "send", "Producer not started"))
        : current.producer.send(id, message);
    },
    stop: Effect.suspend(() => {
      const current = runtime;
      runtime = null;
      return current === null
        ? Effect.void
        : current.producer.flush.pipe(
            Effect.ensuring(Scope.close(current.scope, Exit.void)),
          );
    }),
  };
}
