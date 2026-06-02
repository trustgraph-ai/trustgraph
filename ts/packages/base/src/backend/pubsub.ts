/**
 * Effect-native pub/sub capability for runtime composition.
 *
 * The existing Promise-based backend protocol stays available as the
 * compatibility bridge while service code moves to `Context.Service`/Layers.
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
import { makeNatsBackend } from "./nats.js";
import { pubSubError } from "../errors.js";

export interface PubSubService {
  readonly backend: PubSubBackend;
  readonly createProducer: <T>(
    options: CreateProducerOptions<T>,
  ) => Effect.Effect<BackendProducer<T>, ReturnType<typeof pubSubError>>;
  readonly createConsumer: <T>(
    options: CreateConsumerOptions<T>,
  ) => Effect.Effect<BackendConsumer<T>, ReturnType<typeof pubSubError>>;
  readonly close: Effect.Effect<void, ReturnType<typeof pubSubError>>;
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
    createProducer: <T>(options: CreateProducerOptions<T>) =>
      Effect.tryPromise({
        try: () => backend.createProducer<T>(options),
        catch: (error) => pubSubError(`createProducer:${options.topic}`, error),
      }),
    createConsumer: <T>(options: CreateConsumerOptions<T>) =>
      Effect.tryPromise({
        try: () => backend.createConsumer<T>(options),
        catch: (error) => pubSubError(`createConsumer:${options.topic}`, error),
      }),
    close: Effect.tryPromise({
      try: () => backend.close(),
      catch: (error) => pubSubError("close", error),
    }),
  };
}

export function pubSubLayer(backend: PubSubBackend): Layer.Layer<PubSub> {
  return Layer.effect(PubSub)(
    Effect.gen(function* () {
      const service = makePubSubService(backend);
      yield* Effect.addFinalizer(() =>
        service.close.pipe(
          Effect.catch((error) =>
            Effect.logError("[PubSub] Failed to close backend", {
              error: error.message,
              operation: error.operation,
            }),
          ),
        ),
      );
      return PubSub.of(service);
    }),
  );
}

export function makeNatsPubSubLayer(url = "nats://localhost:4222"): Layer.Layer<PubSub> {
  return pubSubLayer(makeNatsBackend(url));
}

export const NatsPubSubLive = Layer.effect(PubSub)(
  Effect.gen(function* () {
    const natsUrl = O.getOrUndefined(yield* Config.string("NATS_URL").pipe(Config.option));
    const pulsarHost = O.getOrUndefined(yield* Config.string("PULSAR_HOST").pipe(Config.option));
    const service = makePubSubService(makeNatsBackend(natsUrl ?? pulsarHost ?? "nats://localhost:4222"));
    yield* Effect.addFinalizer(() =>
      service.close.pipe(
        Effect.catch((error) =>
          Effect.logError("[PubSub] Failed to close NATS backend", {
            error: error.message,
            operation: error.operation,
          }),
        ),
      ),
    );
    return PubSub.of(service);
  }),
);
