import { describe, expect, it } from "vitest";
import { Effect } from "effect";
import {
  makeProducer,
  pubSubError,
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

  createProducer<T>(options: CreateProducerOptions<T>): Effect.Effect<BackendProducer<T>> {
    return Effect.sync(() => {
      this.producerTopics.push(options.topic);

      return {
        send: (message, properties) => Effect.sync(() => {
        this.sent.push(properties === undefined ? { message } : { message, properties });
        }),
        flush: Effect.suspend(() => {
          this.flushCount += 1;
          if (this.failFlush) {
            return Effect.fail(pubSubError("flush", "flush failed"));
          }
          return Effect.void;
        }),
        close: Effect.sync(() => {
          this.closeCount += 1;
        }),
      };
    });
  }

  createConsumer<T>(_options: CreateConsumerOptions<T>): Effect.Effect<BackendConsumer<T>> {
    return Effect.fail(pubSubError("create-consumer", "consumer not supported"));
  }

  readonly close: Effect.Effect<void> = Effect.void;
}

describe("Producer", () => {
  it("routes the compatibility facade through the scoped Effect producer", async () => {
    const backend = new ProducerBackend();
    const producer = makeProducer<string>(backend, "tg.test.producer");

    await Effect.runPromise(producer.start);
    await Effect.runPromise(producer.send("message-1", "hello"));
    await Effect.runPromise(producer.stop);

    expect(backend.producerTopics).toEqual(["tg.test.producer"]);
    expect(backend.sent).toEqual([
      { message: "hello", properties: { id: "message-1" } },
    ]);
    expect(backend.flushCount).toBe(1);
    expect(backend.closeCount).toBe(1);
    await expect(Effect.runPromise(producer.stop)).resolves.toBeUndefined();

    const error = await Effect.runPromise(
      producer.send("message-2", "late"),
    ).catch((caught: unknown) => caught);
    expect(error).toMatchObject({
      _tag: "MessagingLifecycleError",
      operation: "send",
      resource: "tg.test.producer",
    });
  });

  it("closes the scoped producer when flush fails during stop", async () => {
    const backend = new ProducerBackend();
    const producer = makeProducer<string>(backend, "tg.test.producer");

    await Effect.runPromise(producer.start);
    backend.failFlush = true;

    const error = await Effect.runPromise(producer.stop).catch((caught: unknown) => caught);

    expect(error).toMatchObject({
      _tag: "MessagingDeliveryError",
      operation: "flush",
      topic: "tg.test.producer",
    });
    expect(backend.flushCount).toBe(1);
    expect(backend.closeCount).toBe(1);
  });
});
