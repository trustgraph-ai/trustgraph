import { describe, expect, it } from "@effect/vitest";
import { Effect } from "effect";
import * as S from "effect/Schema";
import type {
  BackendConsumer,
  BackendProducer,
  CreateConsumerOptions,
  CreateProducerOptions,
  Message,
  ProcessorConfig,
  PubSubBackend,
} from "../index.js";
import {
  PubSub,
  makeAsyncProcessor,
  pubSubError,
  runProcessorScoped,
} from "../index.js";

class RuntimeServicesTestError extends S.TaggedErrorClass<RuntimeServicesTestError>()(
  "RuntimeServicesTestError",
  { message: S.String },
) {}

class FakeProducer<T> implements BackendProducer<T> {
  readonly sent: Array<{ readonly message: T; readonly properties?: Record<string, string> }> = [];
  closeCount = 0;
  flushCount = 0;

  send(message: T, properties?: Record<string, string>): Effect.Effect<void> {
    return Effect.sync(() => {
      this.sent.push(
        properties === undefined
          ? { message }
          : { message, properties },
      );
    });
  }

  readonly flush: Effect.Effect<void> = Effect.sync(() => {
    this.flushCount += 1;
  });

  readonly close: Effect.Effect<void> = Effect.sync(() => {
    this.closeCount += 1;
  });
}

class FakeConsumer<T> implements BackendConsumer<T> {
  closeCount = 0;

  receive(): Effect.Effect<Message<T> | null> {
    return Effect.succeed(null);
  }

  acknowledge(): Effect.Effect<void> {
    return Effect.void;
  }

  negativeAcknowledge(): Effect.Effect<void> {
    return Effect.void;
  }

  readonly unsubscribe: Effect.Effect<void> = Effect.void;

  readonly close: Effect.Effect<void> = Effect.sync(() => {
    this.closeCount += 1;
  });
}

class FakePubSubBackend implements PubSubBackend {
  closeCount = 0;
  producerOptions: CreateProducerOptions | null = null;
  consumerOptions: CreateConsumerOptions | null = null;

  createProducer<T>(options: CreateProducerOptions): Effect.Effect<BackendProducer<T>> {
    return Effect.sync(() => {
      this.producerOptions = options;
      return new FakeProducer<T>();
    });
  }

  createConsumer<T>(options: CreateConsumerOptions): Effect.Effect<BackendConsumer<T>> {
    return Effect.sync(() => {
      this.consumerOptions = options;
      return new FakeConsumer<T>();
    });
  }

  readonly close: Effect.Effect<void> = Effect.sync(() => {
    this.closeCount += 1;
  });
}

class FailingProducerBackend extends FakePubSubBackend {
  override createProducer<T>(): Effect.Effect<BackendProducer<T>> {
    return Effect.fail(
      pubSubError("createProducer:tg.test.failure", RuntimeServicesTestError.make({ message: "producer unavailable" })),
    );
  }
}

const makeRecordingProcessor = (
  config: ProcessorConfig,
  events: Array<string>,
) => {
  const processor = makeAsyncProcessor(config, {
    run: (runtime) => Effect.sync(() => {
      events.push(`run:${runtime.config.manageProcessSignals === false ? "effect-signals" : "class-signals"}`);
    }),
  });
  processor.onShutdown(() => Effect.sync(() => {
    events.push("stop");
  }));
  return processor;
};

const makeFailingProcessor = (config: ProcessorConfig) =>
  makeAsyncProcessor(config, {
    run: () => Effect.fail(RuntimeServicesTestError.make({ message: "processor failed" })),
  });

const makeNativeRecordingProcessor = (
  config: ProcessorConfig,
  events: Array<string>,
) => {
  const processor = makeAsyncProcessor<never, PubSub>(config, {
    runEffect: (runtime) =>
      Effect.gen(function* () {
        const pubsub = yield* PubSub;
        events.push(`native:${runtime.config.manageProcessSignals === false ? "effect-signals" : "class-signals"}`);
        events.push(`pubsub:${pubsub.backend.constructor.name}`);
      }),
  });
  processor.onShutdown(() => {
    return Effect.sync(() => {
      events.push("native-stop");
    });
  });
  return processor;
};

describe("Effect runtime services", () => {
  it.effect(
    "provides a compatibility backend through the PubSub service",
    Effect.fnUntraced(function* () {
      const backend = new FakePubSubBackend();

      yield* Effect.scoped(
        Effect.gen(function* () {
          const pubsub = yield* PubSub;
          const producer = yield* pubsub.createProducer<string>({ topic: "tg.test.topic" });
          yield* producer.send("hello", { id: "1" });

          expect(backend.producerOptions).toEqual({ topic: "tg.test.topic" });
          expect(pubsub.backend).toBe(backend);
        }).pipe(Effect.provide(PubSub.layer(backend))),
      );

      expect(backend.closeCount).toBe(1);
    }),
  );

  it.effect(
    "maps backend failures into PubSubError",
    Effect.fnUntraced(function* () {
      const backend = new FailingProducerBackend();

      const error = yield* Effect.scoped(
        Effect.gen(function* () {
          const pubsub = yield* PubSub;
          return yield* pubsub.createProducer<string>({ topic: "tg.test.failure" }).pipe(Effect.flip);
        }).pipe(Effect.provide(PubSub.layer(backend))),
      );

      expect(error._tag).toBe("PubSubError");
      expect(error.operation).toBe("createProducer:tg.test.failure");
      expect(error.message).toBe("producer unavailable");
    }),
  );

  it.effect(
    "runs a processor with injected PubSub and scoped finalization",
    Effect.fnUntraced(function* () {
      const backend = new FakePubSubBackend();
      const events: Array<string> = [];

      yield* Effect.scoped(
        runProcessorScoped(
          {
            id: "recording",
            pubsubUrl: "nats://unused:4222",
            metricsPort: 8000,
            manageProcessSignals: true,
          },
          (config) => makeRecordingProcessor(config, events),
        ).pipe(Effect.provide(PubSub.layer(backend))),
      );

      expect(events).toEqual(["run:effect-signals", "stop"]);
      expect(backend.closeCount).toBe(1);
    }),
  );

  it.effect(
    "runs native processor lifecycle hooks with Effect requirements",
    Effect.fnUntraced(function* () {
      const backend = new FakePubSubBackend();
      const events: Array<string> = [];

      yield* Effect.scoped(
        runProcessorScoped(
          {
            id: "native-recording",
            pubsubUrl: "nats://unused:4222",
            metricsPort: 8000,
            manageProcessSignals: true,
          },
          (config) => makeNativeRecordingProcessor(config, events),
        ).pipe(Effect.provide(PubSub.layer(backend))),
      );

      expect(events).toEqual(["native:effect-signals", "pubsub:FakePubSubBackend", "native-stop"]);
      expect(backend.closeCount).toBe(1);
    }),
  );

  it.effect(
    "maps processor start failures into ProcessorLifecycleError",
    Effect.fnUntraced(function* () {
      const backend = new FakePubSubBackend();

      const error = yield* Effect.scoped(
        runProcessorScoped(
          {
            id: "failing",
            metricsPort: 8000,
            manageProcessSignals: true,
          },
          makeFailingProcessor,
        ).pipe(
          Effect.provide(PubSub.layer(backend)),
          Effect.flip,
        ),
      );

      expect(error._tag).toBe("ProcessorLifecycleError");
      expect(error.operation).toBe("start");
      expect(error.processorId).toBe("failing");
      expect(error.message).toBe("processor failed");
    }),
  );
});
