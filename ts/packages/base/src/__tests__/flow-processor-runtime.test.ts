import { describe, expect, it } from "@effect/vitest";
import { ConfigProvider, Effect, Fiber } from "effect";
import {
  FlowProcessor,
  MessagingRuntimeLive,
  makeProducerSpec,
  PubSub,
  runFlowProcessorDefinitionScoped,
  runProcessorScoped,
  topics,
  type BackendConsumer,
  type BackendProducer,
  type CreateConsumerOptions,
  type CreateProducerOptions,
  type Message,
  type ProcessorConfig,
  type PubSubBackend,
} from "../index.js";

function createMessage<T>(value: T, properties: Record<string, string> = {}): Message<T> {
  return {
    value: () => value,
    properties: () => properties,
  };
}

const waitFor = (condition: () => boolean, label: string) =>
  Effect.tryPromise({
    try: () =>
      new Promise<void>((resolve, reject) => {
        const deadline = Date.now() + 1000;
        const check = () => {
          if (condition()) {
            resolve();
            return;
          }
          if (Date.now() > deadline) {
            reject(new Error(`Timed out waiting for ${label}`));
            return;
          }
          setTimeout(check, 5);
        };
        check();
      }),
    catch: (error) => error,
  });

class RecordingProducer<T> implements BackendProducer<T> {
  readonly sent: Array<{ readonly message: T; readonly properties?: Record<string, string> }> = [];
  closeCount = 0;
  flushCount = 0;

  async send(message: T, properties?: Record<string, string>): Promise<void> {
    this.sent.push(properties === undefined ? { message } : { message, properties });
  }

  async flush(): Promise<void> {
    this.flushCount += 1;
  }

  async close(): Promise<void> {
    this.closeCount += 1;
  }
}

class PushConsumer<T> implements BackendConsumer<T> {
  readonly acknowledged: Array<Message<T>> = [];
  readonly nacked: Array<Message<T>> = [];
  closeCount = 0;
  private readonly messages: Array<Message<T>> = [];
  private readonly waiters: Array<(message: Message<T> | null) => void> = [];
  private closed = false;

  push(message: Message<T>): void {
    const waiter = this.waiters.shift();
    if (waiter !== undefined) {
      waiter(message);
      return;
    }
    this.messages.push(message);
  }

  async receive(): Promise<Message<T> | null> {
    const message = this.messages.shift();
    if (message !== undefined || this.closed) {
      return message ?? null;
    }
    return await new Promise((resolve) => {
      this.waiters.push(resolve);
    });
  }

  async acknowledge(message: Message<T>): Promise<void> {
    this.acknowledged.push(message);
  }

  async negativeAcknowledge(message: Message<T>): Promise<void> {
    this.nacked.push(message);
  }

  async unsubscribe(): Promise<void> {}

  async close(): Promise<void> {
    this.closed = true;
    for (const waiter of this.waiters.splice(0)) {
      waiter(null);
    }
    this.closeCount += 1;
  }
}

class FlowProcessorBackend implements PubSubBackend {
  readonly configConsumer = new PushConsumer<{ readonly version: number; readonly config: Record<string, unknown> }>();
  readonly producerOptions: Array<CreateProducerOptions> = [];
  readonly consumerOptions: Array<CreateConsumerOptions> = [];
  readonly producers: Array<RecordingProducer<unknown>> = [];
  closeCount = 0;

  async createProducer<T>(options: CreateProducerOptions): Promise<BackendProducer<T>> {
    this.producerOptions.push(options);
    const producer = new RecordingProducer<unknown>();
    this.producers.push(producer);
    return producer as BackendProducer<T>;
  }

  async createConsumer<T>(options: CreateConsumerOptions): Promise<BackendConsumer<T>> {
    this.consumerOptions.push(options);
    if (options.topic === topics.configPush) {
      return this.configConsumer as unknown as BackendConsumer<T>;
    }
    return new PushConsumer<T>();
  }

  async close(): Promise<void> {
    this.closeCount += 1;
  }

  pushConfig(version: number, flows: Record<string, unknown>): void {
    this.configConsumer.push(createMessage({ version, config: { flows } }));
  }
}

class TestFlowProcessor extends FlowProcessor {
  constructor(
    config: ProcessorConfig,
    private readonly events: Array<string>,
  ) {
    super(config);
    this.registerSpecification(makeProducerSpec<string>("output"));
    this.registerConfigHandler(async (_config, version) => {
      this.events.push(`handler:${version}`);
    });
  }
}

const fastMessagingConfig = ConfigProvider.layer(
  ConfigProvider.fromEnv({
    TG_CONSUMER_RECEIVE_TIMEOUT_MS: "1",
    TG_CONSUMER_ERROR_BACKOFF_MS: "1",
    TG_RATE_LIMIT_RETRY_MS: "1",
    TG_REQUEST_TIMEOUT_MS: "250",
  }),
);

describe("Effect-native FlowProcessor runtime", () => {
  it.effect(
    "starts, restarts, and removes flow scopes from config pushes",
    Effect.fnUntraced(function* () {
      const backend = new FlowProcessorBackend();
      const events: Array<string> = [];

      yield* Effect.scoped(
        Effect.gen(function* () {
          const fiber = yield* runProcessorScoped(
            {
              id: "flow-processor-test",
              pubsubUrl: "nats://unused:4222",
              metricsPort: 8000,
              manageProcessSignals: true,
            },
            (config) => new TestFlowProcessor(config, events),
          ).pipe(
            Effect.provide(MessagingRuntimeLive),
            Effect.provide(PubSub.layer(backend)),
            Effect.provide(fastMessagingConfig),
            Effect.forkChild,
          );

          yield* waitFor(() => backend.consumerOptions.length === 1, "config subscription");

          backend.pushConfig(1, { default: { topics: { output: "topic-a" } } });
          yield* waitFor(() => backend.producers.length === 1, "first flow producer");
          yield* waitFor(() => backend.configConsumer.acknowledged.length === 1, "first config ack");

          backend.pushConfig(2, { default: { topics: { output: "topic-a" } } });
          yield* waitFor(() => backend.configConsumer.acknowledged.length === 2, "unchanged config ack");
          expect(backend.producers.length).toBe(1);

          backend.pushConfig(3, { default: { topics: { output: "topic-b" } } });
          yield* waitFor(() => backend.producers.length === 2, "restarted flow producer");
          yield* waitFor(() => backend.producers[0]?.closeCount === 1, "old flow close");

          backend.pushConfig(4, {});
          yield* waitFor(() => backend.producers[1]?.closeCount === 1, "removed flow close");

          yield* Fiber.interrupt(fiber);
        }),
      );

      expect(backend.producerOptions.map((options) => options.topic)).toEqual(["topic-a", "topic-b"]);
      expect(events).toEqual(["handler:1", "handler:2", "handler:3", "handler:4"]);
      expect(backend.configConsumer.closeCount).toBeGreaterThanOrEqual(1);
      expect(backend.closeCount).toBe(1);
    }),
  );

  it.effect(
    "runs flow specs without a FlowProcessor subclass",
    Effect.fnUntraced(function* () {
      const backend = new FlowProcessorBackend();
      const events: Array<string> = [];

      yield* Effect.scoped(
        Effect.gen(function* () {
          const fiber = yield* runFlowProcessorDefinitionScoped({
            id: "functional-flow-processor-test",
            pubsub: backend,
            specifications: [makeProducerSpec<string>("output")],
            configHandlers: [
              (_config, version) => Effect.sync(() => {
                events.push(`handler:${version}`);
              }),
            ],
          }).pipe(
            Effect.provide(MessagingRuntimeLive),
            Effect.provide(PubSub.layer(backend)),
            Effect.provide(fastMessagingConfig),
            Effect.forkChild,
          );

          yield* waitFor(() => backend.consumerOptions.length === 1, "config subscription");

          backend.pushConfig(1, { default: { topics: { output: "functional-output" } } });
          yield* waitFor(() => backend.producers.length === 1, "functional flow producer");
          yield* waitFor(() => backend.configConsumer.acknowledged.length === 1, "functional config ack");

          yield* Fiber.interrupt(fiber);
        }),
      );

      expect(backend.producerOptions.map((options) => options.topic)).toEqual(["functional-output"]);
      expect(events).toEqual(["handler:1"]);
      expect(backend.configConsumer.closeCount).toBeGreaterThanOrEqual(1);
      expect(backend.closeCount).toBe(1);
    }),
  );
});
