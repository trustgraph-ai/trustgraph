import { describe, expect, it } from "vitest";
import {
  makeRequestResponse,
  type BackendConsumer,
  type BackendProducer,
  type CreateConsumerOptions,
  type CreateProducerOptions,
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

class WaitingConsumer<T> implements BackendConsumer<T> {
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
    if (message !== undefined || this.closed) return message ?? null;

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

describe("RequestResponse compatibility facade", () => {
  it("routes requests through the Effect-native request-response runtime", async () => {
    const consumer = new WaitingConsumer<string>();
    const backend = new RuntimeBackend(
      consumer as BackendConsumer<unknown>,
      (_message, properties) => {
        consumer.push(createMessage("response", { id: properties?.id ?? "" }));
      },
    );
    const requestor = makeRequestResponse<string, string>({
      pubsub: backend,
      requestTopic: "request-topic",
      responseTopic: "response-topic",
      subscription: "sub",
    });

    await requestor.start();
    const response = await requestor.request("request", { timeoutMs: 250 });
    await requestor.stop();

    expect(response).toBe("response");
    expect(backend.producerOptions).toEqual({ topic: "request-topic" });
    expect(backend.consumerOptions).toEqual({ topic: "response-topic", subscription: "sub" });
    expect(backend.producer.sent[0]?.message).toBe("request");
    expect(consumer.acknowledged.length).toBe(1);
    expect(backend.producer.closeCount).toBe(1);
    expect(consumer.closeCount).toBe(1);
  });

  it("rejects with a tagged timeout error instead of a normal Error", async () => {
    const consumer = new WaitingConsumer<string>();
    const backend = new RuntimeBackend(consumer as BackendConsumer<unknown>);
    const requestor = makeRequestResponse<string, string>({
      pubsub: backend,
      requestTopic: "request-topic",
      responseTopic: "response-topic",
      subscription: "sub",
    });

    await requestor.start();
    const error = await requestor.request("request", { timeoutMs: 5 }).catch((caught: unknown) => caught);
    await requestor.stop();

    expect(error).toMatchObject({
      _tag: "MessagingTimeoutError",
      operation: "request-response",
      timeoutMs: 5,
    });
  });

  it("rejects with a tagged lifecycle error when requested before start", async () => {
    const consumer = new WaitingConsumer<string>();
    const backend = new RuntimeBackend(consumer as BackendConsumer<unknown>);
    const requestor = makeRequestResponse<string, string>({
      pubsub: backend,
      requestTopic: "request-topic",
      responseTopic: "response-topic",
      subscription: "sub",
    });

    const error = await requestor.request("request").catch((caught: unknown) => caught);

    expect(error).toMatchObject({
      _tag: "MessagingLifecycleError",
      operation: "request",
      resource: "request-topic:response-topic",
    });
  });
});
