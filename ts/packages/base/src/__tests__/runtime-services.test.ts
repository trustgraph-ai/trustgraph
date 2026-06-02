import { describe, expect, it } from "@effect/vitest";
import { Effect } from "effect";
import {
  PubSub,
  makeAsyncProcessor,
  runProcessorScoped,
  type BackendConsumer,
  type BackendProducer,
  type CreateConsumerOptions,
  type CreateProducerOptions,
  type Message,
  type ProcessorConfig,
  type PubSubBackend,
} from "../index.js";

class FakeProducer<T> implements BackendProducer<T> {
  readonly sent: Array<{ readonly message: T; readonly properties?: Record<string, string> }> = [];
  closeCount = 0;
  flushCount = 0;

  async send(message: T, properties?: Record<string, string>): Promise<void> {
    this.sent.push(
      properties === undefined
        ? { message }
        : { message, properties },
    );
  }

  async flush(): Promise<void> {
    this.flushCount += 1;
  }

  async close(): Promise<void> {
    this.closeCount += 1;
  }
}

class FakeConsumer<T> implements BackendConsumer<T> {
  closeCount = 0;

  async receive(): Promise<Message<T> | null> {
    return null;
  }

  async acknowledge(): Promise<void> {}

  async negativeAcknowledge(): Promise<void> {}

  async unsubscribe(): Promise<void> {}

  async close(): Promise<void> {
    this.closeCount += 1;
  }
}

class FakePubSubBackend implements PubSubBackend {
  closeCount = 0;
  producerOptions: CreateProducerOptions | null = null;
  consumerOptions: CreateConsumerOptions | null = null;

  async createProducer<T>(options: CreateProducerOptions): Promise<BackendProducer<T>> {
    this.producerOptions = options;
    return new FakeProducer<T>();
  }

  async createConsumer<T>(options: CreateConsumerOptions): Promise<BackendConsumer<T>> {
    this.consumerOptions = options;
    return new FakeConsumer<T>();
  }

  async close(): Promise<void> {
    this.closeCount += 1;
  }
}

class FailingProducerBackend extends FakePubSubBackend {
  override async createProducer<T>(): Promise<BackendProducer<T>> {
    throw new Error("producer unavailable");
  }
}

const makeRecordingProcessor = (
  config: ProcessorConfig,
  events: Array<string>,
) => {
  const processor = makeAsyncProcessor(config, {
    run: async (runtime) => {
      events.push(`run:${runtime.config.manageProcessSignals === false ? "effect-signals" : "class-signals"}`);
    },
  });
  const stop = processor.stop;
  processor.stop = async () => {
    events.push("stop");
    await stop();
  };
  return processor;
};

const makeFailingProcessor = (config: ProcessorConfig) =>
  makeAsyncProcessor(config, {
    run: async () => {
      throw new Error("processor failed");
    },
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
    events.push("native-stop");
    return Promise.resolve();
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
          yield* Effect.promise(() => producer.send("hello", { id: "1" }));

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
