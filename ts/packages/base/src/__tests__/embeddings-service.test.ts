import { describe, expect, it } from "@effect/vitest";
import { ConfigProvider, Effect, Fiber } from "effect";
import {
  Embeddings,
  EmbeddingsService,
  MessagingRuntimeLive,
  PubSub,
  embeddingsError,
  runProcessorScoped,
  topics,
  type BackendConsumer,
  type BackendProducer,
  type CreateConsumerOptions,
  type CreateProducerOptions,
  type EmbeddingsRequest,
  type EmbeddingsResponse,
  type Message,
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

  async send(message: T, properties?: Record<string, string>): Promise<void> {
    this.sent.push(properties === undefined ? { message } : { message, properties });
  }

  async flush(): Promise<void> {}

  async close(): Promise<void> {}
}

class PushConsumer<T> implements BackendConsumer<T> {
  readonly acknowledged: Array<Message<T>> = [];
  readonly nacked: Array<Message<T>> = [];
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
  }
}

class EmbeddingsBackend implements PubSubBackend {
  readonly configConsumer = new PushConsumer<{ readonly version: number; readonly config: Record<string, unknown> }>();
  readonly consumersByTopic = new Map<string, PushConsumer<unknown>>();
  readonly producersByTopic = new Map<string, RecordingProducer<unknown>>();
  closeCount = 0;

  async createProducer<T>(options: CreateProducerOptions): Promise<BackendProducer<T>> {
    const producer = new RecordingProducer<unknown>();
    this.producersByTopic.set(options.topic, producer);
    return producer as BackendProducer<T>;
  }

  async createConsumer<T>(options: CreateConsumerOptions): Promise<BackendConsumer<T>> {
    if (options.topic === topics.configPush) {
      return this.configConsumer as unknown as BackendConsumer<T>;
    }
    const consumer = new PushConsumer<unknown>();
    this.consumersByTopic.set(options.topic, consumer);
    return consumer as BackendConsumer<T>;
  }

  async close(): Promise<void> {
    this.closeCount += 1;
  }

  pushConfig(): void {
    this.configConsumer.push(
      createMessage({
        version: 1,
        config: {
          flows: {
            default: {
              topics: {
                "embeddings-request": "embeddings-request-topic",
                "embeddings-response": "embeddings-response-topic",
              },
            },
          },
        },
      }),
    );
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

describe("EmbeddingsService", () => {
  it.effect(
    "handles embeddings requests through the Embeddings Context service",
    Effect.fnUntraced(function* () {
      const backend = new EmbeddingsBackend();
      const embeddingCalls: Array<{ readonly texts: ReadonlyArray<string>; readonly model?: string }> = [];
      const embeddings = Embeddings.of({
        embed: Effect.fn("TestEmbeddings.embed")((texts: ReadonlyArray<string>, model?: string) => {
          embeddingCalls.push(model === undefined ? { texts } : { texts, model });
          return Effect.succeed(texts.map((text, index) => [text.length, model?.length ?? 0, index]));
        }),
      });

      yield* Effect.scoped(
        Effect.gen(function* () {
          const fiber = yield* runService(backend, embeddings).pipe(Effect.forkChild);

          backend.pushConfig();
          yield* waitFor(() => backend.consumersByTopic.has("embeddings-request-topic"), "embeddings consumer");
          yield* waitFor(() => backend.producersByTopic.has("embeddings-response-topic"), "embeddings producer");

          const input = backend.consumersByTopic.get("embeddings-request-topic") as PushConsumer<EmbeddingsRequest>;
          const output = backend.producersByTopic.get("embeddings-response-topic") as RecordingProducer<EmbeddingsResponse>;

          input.push(createMessage({ text: ["alpha", "beta"], model: "model-a" }, { id: "request-1" }));
          yield* waitFor(() => output.sent.length === 1, "embeddings response");

          expect(embeddingCalls).toEqual([{ texts: ["alpha", "beta"], model: "model-a" }]);
          expect(output.sent).toEqual([
            {
              message: { vectors: [[5, 7, 0], [4, 7, 1]] },
              properties: { id: "request-1" },
            },
          ]);
          expect(input.acknowledged.length).toBe(1);
          expect(input.nacked).toEqual([]);

          yield* Fiber.interrupt(fiber);
        }),
      );

      expect(backend.closeCount).toBe(1);
    }),
  );

  it.effect(
    "returns a wire error response when the Embeddings service fails",
    Effect.fnUntraced(function* () {
      const backend = new EmbeddingsBackend();
      const embeddings = Embeddings.of({
        embed: Effect.fn("FailingEmbeddings.embed")(() =>
          Effect.fail(embeddingsError("test.embed", new Error("provider unavailable"), "test")),
        ),
      });

      yield* Effect.scoped(
        Effect.gen(function* () {
          const fiber = yield* runService(backend, embeddings).pipe(Effect.forkChild);

          backend.pushConfig();
          yield* waitFor(() => backend.consumersByTopic.has("embeddings-request-topic"), "embeddings consumer");
          yield* waitFor(() => backend.producersByTopic.has("embeddings-response-topic"), "embeddings producer");

          const input = backend.consumersByTopic.get("embeddings-request-topic") as PushConsumer<EmbeddingsRequest>;
          const output = backend.producersByTopic.get("embeddings-response-topic") as RecordingProducer<EmbeddingsResponse>;

          input.push(createMessage({ text: ["alpha"] }, { id: "request-1" }));
          yield* waitFor(() => output.sent.length === 1, "embeddings error response");

          expect(output.sent).toEqual([
            {
              message: {
                vectors: [],
                error: {
                  type: "embeddings-error",
                  message: "provider unavailable",
                },
              },
              properties: { id: "request-1" },
            },
          ]);
          expect(input.acknowledged.length).toBe(1);
          expect(input.nacked).toEqual([]);

          yield* Fiber.interrupt(fiber);
        }),
      );
    }),
  );
});

const runService = (
  backend: EmbeddingsBackend,
  embeddings: Embeddings,
) =>
  runProcessorScoped(
    {
      id: "embeddings",
      pubsubUrl: "nats://unused:4222",
      metricsPort: 8000,
      manageProcessSignals: true,
    },
    (config) => new EmbeddingsService(config),
  ).pipe(
    Effect.provideService(Embeddings, embeddings),
    Effect.provide(MessagingRuntimeLive),
    Effect.provide(PubSub.layer(backend)),
    Effect.provide(fastMessagingConfig),
  );
