import { describe, expect, it } from "@effect/vitest";
import { ConfigProvider, Effect, Fiber } from "effect";
import * as EffectChunk from "effect/Chunk";
import * as S from "effect/Schema";
import {
  MessagingRuntimeLive,
  PubSub,
  runProcessorScoped,
  topics,
  type BackendConsumer,
  type BackendProducer,
  type Chunk,
  type CreateConsumerOptions,
  type CreateProducerOptions,
  type Message,
  type PubSubBackend,
  type TextDocument,
} from "@trustgraph/base";
import { ChunkingService } from "../chunking/service.js";
import { recursiveSplit } from "../chunking/recursive-splitter.js";

class WaitForTimeout extends S.TaggedErrorClass<WaitForTimeout>()(
  "WaitForTimeout",
  { label: S.String },
) {}

const isWaitForTimeout = S.is(WaitForTimeout);

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
            reject(WaitForTimeout.make({ label }));
            return;
          }
          setTimeout(check, 5);
        };
        check();
      }),
    catch: (error) => isWaitForTimeout(error) ? error : WaitForTimeout.make({ label }),
  });

class RecordingProducer<T> implements BackendProducer<T> {
  readonly sent: Array<{ readonly message: T; readonly properties?: Record<string, string> }> = [];
  closeCount = 0;
  flushCount = 0;

  send(message: T, properties?: Record<string, string>): Effect.Effect<void> {
    return Effect.sync(() => {
      this.sent.push(properties === undefined ? { message } : { message, properties });
    });
  }

  readonly flush: Effect.Effect<void> = Effect.sync(() => {
    this.flushCount += 1;
  });

  readonly close: Effect.Effect<void> = Effect.sync(() => {
    this.closeCount += 1;
  });
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

  receive(): Effect.Effect<Message<T> | null> {
    return Effect.promise(() => {
      const message = this.messages.shift();
      if (message !== undefined || this.closed) {
        return Promise.resolve(message ?? null);
      }
      return new Promise<Message<T> | null>((resolve) => {
        this.waiters.push(resolve);
      });
    });
  }

  acknowledge(message: Message<T>): Effect.Effect<void> {
    return Effect.sync(() => {
      this.acknowledged.push(message);
    });
  }

  negativeAcknowledge(message: Message<T>): Effect.Effect<void> {
    return Effect.sync(() => {
      this.nacked.push(message);
    });
  }

  readonly unsubscribe: Effect.Effect<void> = Effect.void;

  readonly close: Effect.Effect<void> = Effect.sync(() => {
    this.closed = true;
    for (const waiter of this.waiters.splice(0)) {
      waiter(null);
    }
    this.closeCount += 1;
  });
}

class ChunkingBackend implements PubSubBackend {
  readonly configConsumer = new PushConsumer<{ readonly version: number; readonly config: Record<string, unknown> }>();
  readonly consumersByTopic = new Map<string, PushConsumer<unknown>>();
  readonly producersByTopic = new Map<string, RecordingProducer<unknown>>();
  readonly producerOptions: Array<CreateProducerOptions> = [];
  readonly consumerOptions: Array<CreateConsumerOptions> = [];
  closeCount = 0;

  createProducer<T>(options: CreateProducerOptions): Effect.Effect<BackendProducer<T>> {
    return Effect.sync(() => {
      this.producerOptions.push(options);
      const producer = new RecordingProducer<unknown>();
      this.producersByTopic.set(options.topic, producer);
      return producer as BackendProducer<T>;
    });
  }

  createConsumer<T>(options: CreateConsumerOptions): Effect.Effect<BackendConsumer<T>> {
    return Effect.sync(() => {
      this.consumerOptions.push(options);
      if (options.topic === topics.configPush) {
        return this.configConsumer as unknown as BackendConsumer<T>;
      }
      const consumer = new PushConsumer<unknown>();
      this.consumersByTopic.set(options.topic, consumer);
      return consumer as BackendConsumer<T>;
    });
  }

  readonly close: Effect.Effect<void> = Effect.sync(() => {
    this.closeCount += 1;
  });

  pushConfig(): void {
    this.configConsumer.push(
      createMessage({
        version: 1,
        config: {
          flows: {
            default: {
              topics: {
                "chunk-input": "chunk-input-topic",
                "chunk-output": "chunk-output-topic",
                "chunk-triples": "chunk-triples-topic",
              },
              parameters: {
                "chunk-size": 18,
                "chunk-overlap": 0,
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

describe("ChunkingService", () => {
  it.effect(
    "handles chunk-input with native Effect flow resources",
    Effect.fnUntraced(function* () {
      const backend = new ChunkingBackend();

      yield* Effect.scoped(
        Effect.gen(function* () {
          const fiber = yield* runProcessorScoped(
            {
              id: "chunking",
              pubsubUrl: "nats://unused:4222",
              metricsPort: 8000,
              manageProcessSignals: true,
            },
            (config) => new ChunkingService(config),
          ).pipe(
            Effect.provide(MessagingRuntimeLive),
            Effect.provide(PubSub.layer(backend)),
            Effect.provide(fastMessagingConfig),
            Effect.forkChild,
          );

          backend.pushConfig();
          yield* waitFor(() => backend.consumersByTopic.has("chunk-input-topic"), "chunk consumer");
          yield* waitFor(() => backend.producersByTopic.has("chunk-output-topic"), "chunk producer");

          const document: TextDocument = {
            documentId: "doc-1",
            metadata: {
              id: "pipeline-1",
              root: "root-1",
              user: "user-1",
              collection: "collection-1",
            },
            text: "alpha beta gamma delta epsilon zeta eta theta",
          };
          const inputConsumer = backend.consumersByTopic.get("chunk-input-topic") as PushConsumer<TextDocument>;
          inputConsumer.push(createMessage(document, { id: "request-1" }));

          const outputProducer = backend.producersByTopic.get("chunk-output-topic") as RecordingProducer<Chunk>;
          const expectedChunks = EffectChunk.toReadonlyArray(recursiveSplit(document.text, 18, 0));
          yield* waitFor(() => outputProducer.sent.length === expectedChunks.length, "chunk outputs");

          expect(inputConsumer.acknowledged.length).toBe(1);
          expect(inputConsumer.nacked).toEqual([]);
          expect(outputProducer.sent.map(({ message }) => message.chunk)).toEqual(expectedChunks);
          expect(outputProducer.sent.every(({ properties }) => properties?.id === "request-1")).toBe(true);

          yield* Fiber.interrupt(fiber);
        }),
      );

      expect(backend.closeCount).toBe(1);
    }),
  );
});
