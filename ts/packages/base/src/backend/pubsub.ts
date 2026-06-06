/**
 * Effect-native pub/sub capability for runtime composition.
 *
 * The backend protocol is Effect-native; this service provides the
 * Context.Service/Layer boundary used by runtime composition.
 */

import { Config, Context, Effect, Layer } from "effect";
import * as O from "effect/Option";
import type {
  BackendConsumer,
  BackendProducer,
  CreateConsumerOptions,
  CreateProducerOptions,
  PubSubBackend,
} from "./types.js";
import { makeNatsBackendScoped } from "./nats.js";
import type { PubSubError } from "../errors.js";

export interface PubSubService {
  readonly backend: PubSubBackend;
  readonly createProducer: <T>(
    options: CreateProducerOptions<T>,
  ) => Effect.Effect<BackendProducer<T>, PubSubError>;
  readonly createConsumer: <T>(
    options: CreateConsumerOptions<T>,
  ) => Effect.Effect<BackendConsumer<T>, PubSubError>;
  readonly close: Effect.Effect<void, PubSubError>;
}

export class PubSub extends Context.Service<PubSub, PubSubService>()("@trustgraph/base/backend/pubsub") {
  static fromBackend(backend: PubSubBackend): PubSubService {
    return makePubSubService(backend);
  }

  static layer(backend: PubSubBackend): Layer.Layer<PubSub> {
    return pubSubLayer(backend);
  }
}

export function makePubSubService(backend: PubSubBackend): PubSubService {
  return {
    backend,
    createProducer: <T>(options: CreateProducerOptions<T>) => backend.createProducer<T>(options),
    createConsumer: <T>(options: CreateConsumerOptions<T>) => backend.createConsumer<T>(options),
    close: backend.close,
  };
}

export function pubSubLayer(backend: PubSubBackend): Layer.Layer<PubSub> {
  return Layer.effect(PubSub)(
    Effect.acquireRelease(
      Effect.sync(() => makePubSubService(backend)),
      (service) =>
        service.close.pipe(
          Effect.catch((error) =>
            Effect.logError("[PubSub] Failed to close backend", {
              error: error.message,
              operation: error.operation,
            }),
          ),
        )
    ).pipe(
      Effect.map(PubSub.of),
    ),
  );
}

export function makeNatsPubSubLayer(url = "nats://localhost:4222"): Layer.Layer<PubSub> {
  return Layer.effect(PubSub)(
    makeNatsBackendScoped(url).pipe(
      Effect.map(makePubSubService),
      Effect.map(PubSub.of),
    ),
  );
}

export const NatsPubSubLive = Layer.effect(PubSub)(
  Effect.gen(function* () {
    const natsUrl = O.getOrUndefined(yield* Config.string("NATS_URL").pipe(Config.option));
    const pulsarHost = O.getOrUndefined(yield* Config.string("PULSAR_HOST").pipe(Config.option));
    const backend = yield* makeNatsBackendScoped(natsUrl ?? pulsarHost ?? "nats://localhost:4222");
    const service = makePubSubService(backend);
    return PubSub.of(service);
  }),
);
