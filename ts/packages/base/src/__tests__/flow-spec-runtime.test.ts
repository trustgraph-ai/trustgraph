import { describe, expect, it } from "@effect/vitest";
import { ConfigProvider, Duration, Effect, Fiber } from "effect";
import * as TestClock from "effect/testing/TestClock";
import {
  makeConsumerSpec,
  makeConsumerSpecFromPromise,
  Flow,
  MessagingRuntimeLive,
  makeParameterSpec,
  makeProducerSpec,
  PubSub,
  makeRequestResponseSpec,
  type BackendConsumer,
  type BackendProducer,
  type CreateConsumerOptions,
  type CreateProducerOptions,
  type FlowContext,
  type Message,
  type PubSubBackend,
} from "../index.js";

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
  private readonly waiters: Array<(message: Message<T> | null) => void> = [];
  private closed = false;

  constructor(
    messages: Array<Message<T>> = [],
    private readonly waitForMessages = false,
  ) {
    this.messages = messages;
  }

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
    if (message !== undefined || !this.waitForMessages || this.closed) {
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

const fastMessagingConfig = ConfigProvider.layer(
  ConfigProvider.fromEnv({
    TG_CONSUMER_RECEIVE_TIMEOUT_MS: "1",
    TG_CONSUMER_ERROR_BACKOFF_MS: "1",
    TG_RATE_LIMIT_RETRY_MS: "1",
    TG_REQUEST_TIMEOUT_MS: "250",
  }),
);

const provideRuntime = <A, E, R>(
  backend: RuntimeBackend,
  effect: Effect.Effect<A, E, R>,
) =>
  effect.pipe(
    Effect.provide(MessagingRuntimeLive),
    Effect.provideService(PubSub, PubSub.fromBackend(backend)),
    Effect.provide(fastMessagingConfig),
  );

describe("Effect-native flow specifications", () => {
  it.effect(
    "starts producer specs through Effect factories and exposes typed accessors",
    Effect.fnUntraced(function* () {
      const backend = new RuntimeBackend(new ScriptedConsumer<unknown>());
      const flow = new Flow(
        "default",
        "processor",
        backend,
        { topics: { output: "actual-output" } },
        [makeProducerSpec<string>("output")],
      );

      yield* Effect.scoped(
        provideRuntime(
          backend,
          Effect.gen(function* () {
            yield* flow.startEffect();
            const producer = yield* flow.producerEffect<string>("output");
            yield* producer.send("request-1", "hello");
          }),
        ),
      );

      expect(backend.producerOptions).toEqual({ topic: "actual-output" });
      expect(backend.producer.sent).toEqual([
        { message: "hello", properties: { id: "request-1" } },
      ]);
      expect(backend.producer.closeCount).toBe(1);
    }),
  );

  it.effect(
    "runs Promise handlers through the explicit makeConsumerSpec compatibility helper",
    Effect.fnUntraced(function* () {
      const message = createMessage("payload", { id: "request-1" });
      const consumer = new ScriptedConsumer<string>([message]);
      const backend = new RuntimeBackend(consumer as BackendConsumer<unknown>);
      const handled: Array<string> = [];
      const flow = new Flow(
        "default",
        "processor",
        backend,
        {},
        [
          makeConsumerSpecFromPromise<string>(
            "input",
            async (value, properties, flowContext: FlowContext) => {
              handled.push(`${flowContext.name}:${properties.id}:${value}`);
            },
          ),
        ],
      );

      yield* Effect.scoped(
        provideRuntime(
          backend,
          Effect.gen(function* () {
            yield* flow.startEffect();
            yield* Effect.yieldNow;
            yield* TestClock.adjust(Duration.millis(5));
          }),
        ),
      );

      expect(consumer.acknowledged).toEqual([message]);
      expect(consumer.nacked).toEqual([]);
      expect(handled).toEqual(["default:request-1:payload"]);
    }),
  );

  it.effect(
    "registers request-response specs through Effect queues and keeps the Promise facade working",
    Effect.fnUntraced(function* () {
      const responseConsumer = new ScriptedConsumer<string>([], true);
      const backend = new RuntimeBackend(
        responseConsumer as BackendConsumer<unknown>,
        (_message, properties) => {
          responseConsumer.push(createMessage("response", { id: properties?.id ?? "" }));
        },
      );
      const flow = new Flow(
        "default",
        "processor",
        backend,
        {
          topics: {
            request: "actual-request",
            response: "actual-response",
          },
        },
        [makeRequestResponseSpec<string, string>("rr", "request", "response")],
      );

      const response = yield* Effect.scoped(
        provideRuntime(
          backend,
          Effect.gen(function* () {
            yield* flow.startEffect();
            const requestor = flow.requestor<string, string>("rr");
            const fiber = yield* Effect.promise(() =>
              requestor.request("request", { timeoutMs: 250 }),
            ).pipe(Effect.forkChild);
            yield* TestClock.adjust(Duration.millis(5));
            return yield* Fiber.join(fiber);
          }),
        ),
      );

      expect(response).toBe("response");
      expect(backend.producerOptions).toEqual({ topic: "actual-request" });
      expect(responseConsumer.acknowledged.length).toBe(1);
    }),
  );

  it.effect(
    "returns typed errors for missing flow resources",
    Effect.fnUntraced(function* () {
      const backend = new RuntimeBackend(new ScriptedConsumer<unknown>());
      const flow = new Flow(
        "default",
        "processor",
        backend,
        { parameters: { present: 42 } },
        [makeParameterSpec("present")],
      );

      const errors = yield* Effect.scoped(
        provideRuntime(
          backend,
          Effect.gen(function* () {
            yield* flow.startEffect();
            const producerError = yield* flow.producerEffect<string>("missing-producer").pipe(Effect.flip);
            const parameter = yield* flow.parameterEffect<number>("present");
            const parameterError = yield* flow.parameterEffect<number>("missing-parameter").pipe(Effect.flip);
            return { producerError, parameter, parameterError };
          }),
        ),
      );

      expect(errors.parameter).toBe(42);
      expect(errors.producerError._tag).toBe("FlowResourceNotFoundError");
      expect(errors.producerError.resourceType).toBe("producer");
      expect(errors.producerError.resourceName).toBe("missing-producer");
      expect(errors.parameterError._tag).toBe("FlowResourceNotFoundError");
      expect(errors.parameterError.resourceType).toBe("parameter");
      expect(() => flow.producer("missing-producer")).toThrow("not found");
    }),
  );
});
