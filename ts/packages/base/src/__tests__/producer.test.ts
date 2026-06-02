import { describe, expect, it } from "vitest";
import {
  makeProducer,
  type BackendConsumer,
  type BackendProducer,
  type CreateConsumerOptions,
  type CreateProducerOptions,
  type PubSubBackend,
} from "../index.js";

class ProducerBackend implements PubSubBackend {
  readonly sent: Array<{ readonly message: unknown; readonly properties?: Record<string, string> }> = [];
  readonly producerTopics: Array<string> = [];
  closeCount = 0;
  flushCount = 0;
  failFlush = false;

  async createProducer<T>(options: CreateProducerOptions<T>): Promise<BackendProducer<T>> {
    this.producerTopics.push(options.topic);

    return {
      send: async (message, properties) => {
        this.sent.push(properties === undefined ? { message } : { message, properties });
      },
      flush: async () => {
        this.flushCount += 1;
        if (this.failFlush) {
          return Promise.reject("flush failed");
        }
      },
      close: async () => {
        this.closeCount += 1;
      },
    };
  }

  createConsumer<T>(_options: CreateConsumerOptions<T>): Promise<BackendConsumer<T>> {
    return Promise.reject("consumer not supported");
  }

  async close(): Promise<void> {}
}

describe("Producer", () => {
  it("routes the compatibility facade through the scoped Effect producer", async () => {
    const backend = new ProducerBackend();
    const producer = makeProducer<string>(backend, "tg.test.producer");

    await producer.start();
    await producer.send("message-1", "hello");
    await producer.stop();

    expect(backend.producerTopics).toEqual(["tg.test.producer"]);
    expect(backend.sent).toEqual([
      { message: "hello", properties: { id: "message-1" } },
    ]);
    expect(backend.flushCount).toBe(1);
    expect(backend.closeCount).toBe(1);
    await expect(producer.stop()).resolves.toBeUndefined();

    const error = await producer.send("message-2", "late").catch((caught: unknown) => caught);
    expect(error).toMatchObject({
      _tag: "MessagingLifecycleError",
      operation: "send",
      resource: "tg.test.producer",
    });
  });

  it("closes the scoped producer when flush fails during stop", async () => {
    const backend = new ProducerBackend();
    const producer = makeProducer<string>(backend, "tg.test.producer");

    await producer.start();
    backend.failFlush = true;

    const error = await producer.stop().catch((caught: unknown) => caught);

    expect(error).toMatchObject({
      _tag: "MessagingDeliveryError",
      operation: "flush",
      topic: "tg.test.producer",
    });
    expect(backend.flushCount).toBe(1);
    expect(backend.closeCount).toBe(1);
  });
});
