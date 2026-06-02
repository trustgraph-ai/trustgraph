import { describe, expect, it } from "@effect/vitest";
import { Duration, Effect, Fiber } from "effect";
import * as TestClock from "effect/testing/TestClock";
import {
  PubSub,
  defaultMessagingRuntimeConfig,
  makeEffectRequestResponseFromPubSub,
  MessagingRuntimeLive,
  makeProducerSpec,
  runEffectConsumerScoped,
  runEffectProducerScoped,
  runFlowScoped,
  type BackendConsumer,
  type BackendProducer,
  type CreateConsumerOptions,
  type CreateProducerOptions,
  type FlowContext,
  type Message,
  type PubSubBackend,
} from "../index.js";
import type { Flow } from "../processor/flow.js";
import { Flow as RuntimeFlow } from "../processor/flow.js";

function createMessage<T>(value: T, properties: Record<string, string> = {}): Message<T> {
  return {
    value: () => value,
    properties: () => properties,
  };
}

class RecordingProducer<T> implements BackendProducer<T> {
  readonly sent: Array<{ readonly message: T; readonly properties?: Record<string, string> }> = [];
  closeCount = 0;
  flushCount = 0;

  constructor(private readonly onSend?: (message: T, properties?: Record<string, string>) => void) {}

  async send(message: T, properties?: Record<string, string>): Promise<void> {
    this.sent.push(properties === undefined ? { message } : { message, properties });
    this.onSend?.(message, properties);
  }

  async flush(): Promise<void> {
    this.flushCount += 1;
  }

  async close(): Promise<void> {
    this.closeCount += 1;
  }
}

class ScriptedConsumer<T> implements BackendConsumer<T> {
  readonly acknowledged: Array<Message<T>> = [];
  readonly nacked: Array<Message<T>> = [];
  closeCount = 0;
  private readonly messages: Array<Message<T>>;

  constructor(messages: Array<Message<T>> = []) {
    this.messages = messages;
  }

  push(message: Message<T>): void {
    this.messages.push(message);
  }

  async receive(): Promise<Message<T> | null> {
    const message = this.messages.shift();
    if (message !== undefined) {
      return message;
    }
    return null;
  }

  async acknowledge(message: Message<T>): Promise<void> {
    this.acknowledged.push(message);
  }

  async negativeAcknowledge(message: Message<T>): Promise<void> {
    this.nacked.push(message);
  }

  async unsubscribe(): Promise<void> {}

  async close(): Promise<void> {
    this.closeCount += 1;
  }
}

class RuntimeBackend implements PubSubBackend {
  closeCount = 0;
  producerOptions: CreateProducerOptions | null = null;
  consumerOptions: CreateConsumerOptions | null = null;
  readonly producer: RecordingProducer<unknown>;

  constructor(
    private readonly consumer: BackendConsumer<unknown>,
    onSend?: (message: unknown, properties?: Record<string, string>) => void,
  ) {
    this.producer = new RecordingProducer<unknown>(onSend);
  }

  async createProducer<T>(options: CreateProducerOptions): Promise<BackendProducer<T>> {
    this.producerOptions = options;
    return this.producer as BackendProducer<T>;
  }

  async createConsumer<T>(options: CreateConsumerOptions): Promise<BackendConsumer<T>> {
    this.consumerOptions = options;
    return this.consumer as BackendConsumer<T>;
  }

  async close(): Promise<void> {
    this.closeCount += 1;
  }
}

const flowContext: FlowContext = {
  id: "processor",
  name: "default",
  flow: {} as Flow,
};

describe("Effect-native messaging runtime", () => {
  it.effect(
    "creates scoped producers through PubSub and translates send calls",
    Effect.fnUntraced(function* () {
      const consumer = new ScriptedConsumer<unknown>();
      const backend = new RuntimeBackend(consumer);

      yield* Effect.scoped(
        Effect.gen(function* () {
          const producer = yield* runEffectProducerScoped<string>({ topic: "tg.test.producer" });
          yield* producer.send("message-1", "hello");

          expect(backend.producerOptions).toEqual({ topic: "tg.test.producer" });
          expect(backend.producer.sent).toEqual([
            { message: "hello", properties: { id: "message-1" } },
          ]);
        }).pipe(Effect.provide(PubSub.layer(backend))),
      );

      expect(backend.producer.closeCount).toBe(1);
      expect(backend.closeCount).toBe(1);
    }),
  );

  it.effect(
    "runs consumers as scoped fibers and acknowledges handled messages",
    Effect.fnUntraced(function* () {
      const message = createMessage("payload", { id: "request-1" });
      const consumer = new ScriptedConsumer<string>([message]);
      const backend = new RuntimeBackend(consumer as BackendConsumer<unknown>);
      const handled: Array<string> = [];

      yield* Effect.scoped(
        Effect.gen(function* () {
          yield* runEffectConsumerScoped<string>(
            {
              topic: "tg.test.consumer",
              subscription: "sub",
              receiveTimeoutMs: 1,
              errorBackoffMs: 1,
              handler: (value, properties) =>
                Effect.sync(() => {
                  handled.push(`${properties.id}:${value}`);
                }),
            },
            flowContext,
          );
          yield* TestClock.adjust(Duration.millis(20));
        }).pipe(Effect.provide(PubSub.layer(backend))),
      );

      expect(handled).toEqual(["request-1:payload"]);
      expect(consumer.acknowledged).toEqual([message]);
      expect(consumer.nacked).toEqual([]);
      expect(consumer.closeCount).toBeGreaterThan(0);
    }),
  );

  it.effect(
    "routes request-response replies through an Effect queue",
    Effect.fnUntraced(function* () {
      const responseConsumer = new ScriptedConsumer<string>();
      const backend = new RuntimeBackend(
        responseConsumer as BackendConsumer<unknown>,
        (_message, properties) => {
          responseConsumer.push(createMessage("response", { id: properties?.id ?? "" }));
        },
      );

      const response = yield* Effect.scoped(
        Effect.gen(function* () {
          const requestor = yield* makeEffectRequestResponseFromPubSub<string, string>(
            PubSub.fromBackend(backend),
            {
              ...defaultMessagingRuntimeConfig,
              consumerReceiveTimeoutMs: 1,
            },
            {
              requestTopic: "tg.test.request",
              responseTopic: "tg.test.response",
              subscription: "sub",
            },
          );
          const fiber = yield* requestor.request("request", { timeoutMs: 250 }).pipe(Effect.forkChild);
          yield* TestClock.adjust(Duration.millis(5));
          return yield* Fiber.join(fiber);
        }),
      );

      expect(response).toBe("response");
      expect(backend.producer.sent[0]?.message).toBe("request");
      expect(responseConsumer.acknowledged.length).toBe(1);
    }),
  );

  it.effect(
    "waits until the request recipient accepts a response",
    Effect.fnUntraced(function* () {
      const responseConsumer = new ScriptedConsumer<unknown>();
      const backend = new RuntimeBackend(
        responseConsumer,
        (_message, properties) => {
          const id = properties?.id ?? "";
          responseConsumer.push(createMessage("partial", { id }));
          responseConsumer.push(createMessage("final", { id }));
        },
      );
      const seen: Array<string> = [];

      const response = yield* Effect.scoped(
        Effect.gen(function* () {
          const requestor = yield* makeEffectRequestResponseFromPubSub<string, string>(
            PubSub.fromBackend(backend),
            {
              ...defaultMessagingRuntimeConfig,
              consumerReceiveTimeoutMs: 1,
            },
            {
              requestTopic: "tg.test.request",
              responseTopic: "tg.test.response",
              subscription: "sub",
            },
          );
          const fiber = yield* requestor.request("request", {
            timeoutMs: 250,
            recipient: (candidate) =>
              Effect.sync(() => {
                seen.push(candidate);
                return candidate === "final";
              }),
          }).pipe(Effect.forkChild);
          yield* TestClock.adjust(Duration.millis(5));
          return yield* Fiber.join(fiber);
        }),
      );

      expect(response).toBe("final");
      expect(seen).toEqual(["partial", "final"]);
      expect(responseConsumer.acknowledged.length).toBe(2);
    }),
  );

  it.effect(
    "fails request-response calls with a typed timeout",
    Effect.fnUntraced(function* () {
      const responseConsumer = new ScriptedConsumer<string>();
      const backend = new RuntimeBackend(responseConsumer as BackendConsumer<unknown>);

      const error = yield* Effect.scoped(
        Effect.gen(function* () {
          const requestor = yield* makeEffectRequestResponseFromPubSub<string, string>(
            PubSub.fromBackend(backend),
            {
              ...defaultMessagingRuntimeConfig,
              consumerReceiveTimeoutMs: 1,
            },
            {
              requestTopic: "tg.test.request",
              responseTopic: "tg.test.response",
              subscription: "sub",
            },
          );
          const fiber = yield* requestor.request("request", { timeoutMs: 5 }).pipe(
            Effect.flip,
            Effect.forkChild,
          );
          yield* TestClock.adjust(Duration.millis(10));
          return yield* Fiber.join(fiber);
        }),
      );

      expect(error._tag).toBe("MessagingTimeoutError");
      expect(error.operation).toBe("request-response");
      expect(error.timeoutMs).toBe(5);
    }),
  );

  it.effect(
    "owns Flow lifecycle through a scoped Effect boundary",
    Effect.fnUntraced(function* () {
      const consumer = new ScriptedConsumer<unknown>();
      const backend = new RuntimeBackend(consumer);
      const flow = new RuntimeFlow(
        "flow-a",
        "processor",
        backend,
        {},
        [makeProducerSpec<string>("flow-output")],
      );

      yield* Effect.scoped(
        runFlowScoped(flow).pipe(
          Effect.provide(MessagingRuntimeLive),
          Effect.provideService(PubSub, PubSub.fromBackend(backend)),
        ),
      );

      expect(backend.producerOptions).toEqual({ topic: "flow-output" });
      expect(backend.producer.closeCount).toBe(1);
    }),
  );
});
