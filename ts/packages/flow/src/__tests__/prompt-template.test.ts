import { describe, expect, it } from "@effect/vitest";
import { ConfigProvider, Effect, Fiber } from "effect";
import * as S from "effect/Schema";
import type {
  BackendConsumer,
  BackendProducer,
  CreateConsumerOptions,
  CreateProducerOptions,
  Message,
  PromptRequest,
  PromptResponse,
  PubSubBackend,
} from "@trustgraph/base";
import {
  MessagingRuntimeLive,
  PubSub,
  runProcessorScoped,
  topics,
} from "@trustgraph/base";
import { PromptTemplateService } from "../prompt/template.js";

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

  send(message: T, properties?: Record<string, string>): Effect.Effect<void> {
    return Effect.sync(() => {
      this.sent.push(properties === undefined ? { message } : { message, properties });
    });
  }

  readonly flush: Effect.Effect<void> = Effect.void;

  readonly close: Effect.Effect<void> = Effect.void;
}

class PushConsumer<T> implements BackendConsumer<T> {
  readonly acknowledged: Array<Message<T>> = [];
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

  negativeAcknowledge(): Effect.Effect<void> {
    return Effect.void;
  }

  readonly unsubscribe: Effect.Effect<void> = Effect.void;

  readonly close: Effect.Effect<void> = Effect.sync(() => {
    this.closed = true;
    for (const waiter of this.waiters.splice(0)) {
      waiter(null);
    }
  });
}

class PromptBackend implements PubSubBackend {
  readonly configConsumer = new PushConsumer<{ readonly version: number; readonly config: Record<string, unknown> }>();
  readonly consumersByTopic = new Map<string, PushConsumer<unknown>>();
  readonly producersByTopic = new Map<string, RecordingProducer<unknown>>();

  createProducer<T>(options: CreateProducerOptions): Effect.Effect<BackendProducer<T>> {
    return Effect.sync(() => {
      const producer = new RecordingProducer<unknown>();
      this.producersByTopic.set(options.topic, producer);
      return producer as BackendProducer<T>;
    });
  }

  createConsumer<T>(options: CreateConsumerOptions): Effect.Effect<BackendConsumer<T>> {
    return Effect.sync(() => {
      if (options.topic === topics.configPush) {
        return this.configConsumer as unknown as BackendConsumer<T>;
      }
      const consumer = new PushConsumer<unknown>();
      this.consumersByTopic.set(options.topic, consumer);
      return consumer as BackendConsumer<T>;
    });
  }

  readonly close: Effect.Effect<void> = Effect.void;

  pushPromptConfig(): void {
    this.configConsumer.push(createMessage({
      version: 1,
      config: {
        flows: {
          default: {
            topics: {
              "prompt-request": "prompt-request-topic",
              "prompt-response": "prompt-response-topic",
            },
          },
        },
        prompt: {
          greeting: {
            system: "System for {name}",
            prompt: "Hello {name} from {place}",
          },
        },
      },
    }));
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

describe("PromptTemplateService", () => {
  it.effect(
    "renders prompt templates loaded from config through MutableHashMap state",
    Effect.fnUntraced(function* () {
      const backend = new PromptBackend();

      yield* Effect.scoped(
        Effect.gen(function* () {
          const fiber = yield* runProcessorScoped(
            {
              id: "prompt",
              pubsubUrl: "nats://unused:4222",
              metricsPort: 8000,
              manageProcessSignals: true,
            },
            (config) => new PromptTemplateService(config),
          ).pipe(
            Effect.provide(MessagingRuntimeLive),
            Effect.provide(PubSub.layer(backend)),
            Effect.provide(fastMessagingConfig),
            Effect.forkChild,
          );

          backend.pushPromptConfig();
          yield* waitFor(() => backend.consumersByTopic.has("prompt-request-topic"), "prompt consumer");
          yield* waitFor(() => backend.producersByTopic.has("prompt-response-topic"), "prompt producer");
          yield* waitFor(() => backend.configConsumer.acknowledged.length === 1, "config ack");

          const inputConsumer = backend.consumersByTopic.get("prompt-request-topic") as PushConsumer<PromptRequest>;
          const outputProducer = backend.producersByTopic.get("prompt-response-topic") as RecordingProducer<PromptResponse>;

          inputConsumer.push(createMessage({
            name: "greeting",
            variables: {
              name: "Ada",
              place: "TrustGraph",
            },
          }, { id: "request-1" }));

          yield* waitFor(() => outputProducer.sent.length === 1, "prompt response");

          expect(inputConsumer.acknowledged.length).toBe(1);
          expect(outputProducer.sent).toEqual([
            {
              message: {
                system: "System for Ada",
                prompt: "Hello Ada from TrustGraph",
              },
              properties: { id: "request-1" },
            },
          ]);

          yield* Fiber.interrupt(fiber);
        }),
      );
    }),
  );
});
