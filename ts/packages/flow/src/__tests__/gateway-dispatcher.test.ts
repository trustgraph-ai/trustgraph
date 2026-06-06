import { describe, expect, it } from "vitest";
import { Effect } from "effect";
import {
  dispatcherManagerIsCompleteResponse,
  makeDispatcherManager,
} from "../gateway/dispatch/manager.js";
import {
  clientTermToInternal,
  internalTermToClient,
  translateRequestEffect,
  translateResponseEffect,
} from "../gateway/dispatch/serialize.js";
import type {
  BackendConsumer,
  BackendProducer,
  CreateConsumerOptions,
  CreateProducerOptions,
  Message,
  PubSubBackend,
} from "@trustgraph/base";
import { pubSubError } from "@trustgraph/base";

function createMessage<T>(value: T, properties: Record<string, string> = {}): Message<T> {
  return {
    value: () => value,
    properties: () => properties,
  };
}

class TopicConsumer<T> implements BackendConsumer<T> {
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
      if (message !== undefined || this.closed) return Promise.resolve(message ?? null);

      return new Promise((resolve) => {
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

class RecordingProducer<T> implements BackendProducer<T> {
  readonly sent: Array<{ readonly message: T; readonly properties?: Record<string, string> }> = [];
  closeCount = 0;
  flushCount = 0;

  constructor(
    private readonly topic: string,
    private readonly onSend: (topic: string, message: T, properties?: Record<string, string>) => void,
  ) {}

  send(message: T, properties?: Record<string, string>): Effect.Effect<void> {
    return Effect.try({
      try: () => {
        this.sent.push(properties === undefined ? { message } : { message, properties });
        this.onSend(this.topic, message, properties);
      },
      catch: (error) => pubSubError(`send:${this.topic}`, error),
    });
  }

  readonly flush: Effect.Effect<void> = Effect.sync(() => {
    this.flushCount += 1;
  });

  readonly close: Effect.Effect<void> = Effect.sync(() => {
    this.closeCount += 1;
  });
}

class DispatchBackend implements PubSubBackend {
  closeCount = 0;
  readonly producerOptions: CreateProducerOptions[] = [];
  readonly consumerOptions: CreateConsumerOptions[] = [];
  readonly producersByTopic = new Map<string, RecordingProducer<unknown>>();
  readonly consumersByTopic = new Map<string, TopicConsumer<unknown>>();
  readonly failSendTopics = new Set<string>();

  createProducer<T>(options: CreateProducerOptions): Effect.Effect<BackendProducer<T>> {
    return Effect.sync(() => {
      this.producerOptions.push(options);
      let producer = this.producersByTopic.get(options.topic);
      if (producer === undefined) {
        producer = new RecordingProducer<unknown>(options.topic, (topic, message, properties) => {
          this.handleSend(topic, message, properties);
        });
        this.producersByTopic.set(options.topic, producer);
      }
      return producer as BackendProducer<T>;
    });
  }

  createConsumer<T>(options: CreateConsumerOptions): Effect.Effect<BackendConsumer<T>> {
    return Effect.sync(() => {
      this.consumerOptions.push(options);
      let consumer = this.consumersByTopic.get(options.topic);
      if (consumer === undefined) {
        consumer = new TopicConsumer<unknown>();
        this.consumersByTopic.set(options.topic, consumer);
      }
      return consumer as BackendConsumer<T>;
    });
  }

  readonly close: Effect.Effect<void> = Effect.sync(() => {
    this.closeCount += 1;
  });

  private handleSend(topic: string, message: unknown, properties?: Record<string, string>): void {
    if (this.failSendTopics.has(topic)) {
      throw "send failed";
    }

    const id = properties?.id ?? "";
    if (topic === "tg.flow.config-request") {
      this.push("tg.flow.config-response", { ok: true, echo: message }, id);
      return;
    }

    if (topic === "tg.flow.knowledge-request") {
      this.push("tg.flow.knowledge-response", { chunk: 1 }, id);
      this.push("tg.flow.knowledge-response", { chunk: 2, endOfStream: true }, id);
      return;
    }

    if (topic === "tg.flow.prompt-request") {
      this.push("tg.flow.prompt-response", { prompt: message }, id);
    }
  }

  private push(topic: string, response: unknown, id: string): void {
    const consumer = this.consumersByTopic.get(topic);
    consumer?.push(createMessage(response, { id }));
  }
}

describe("gateway dispatcher manager", () => {
  it("translates compact client terms with Match and schema-backed narrowing", async () => {
    const internal = clientTermToInternal({
      t: "t",
      tr: {
        s: { t: "i", i: "urn:s" },
        p: { t: "b", d: "blank" },
        o: { t: "l", v: "value", dt: "urn:datatype", ln: "en" },
        g: "urn:graph",
      },
    });

    expect(internal).toEqual({
      type: "TRIPLE",
      triple: {
        s: { type: "IRI", iri: "urn:s" },
        p: { type: "BLANK", id: "blank" },
        o: {
          type: "LITERAL",
          value: "value",
          datatype: "urn:datatype",
          language: "en",
        },
        g: "urn:graph",
      },
    });

    expect(internalTermToClient(internal)).toEqual({
      t: "t",
      tr: {
        s: { t: "i", i: "urn:s" },
        p: { t: "b", d: "blank" },
        o: { t: "l", v: "value", dt: "urn:datatype", ln: "en" },
        g: "urn:graph",
      },
    });
  });

  it("deep-translates only schema-valid term-shaped values", async () => {
    const request = await Effect.runPromise(
      translateRequestEffect("knowledge", {
        term: { t: "i", i: "urn:item" },
        malformedKnownTag: { t: "i" },
        untouched: { t: "unknown", value: "kept" },
      }),
    );
    const response = await Effect.runPromise(
      translateResponseEffect("knowledge", {
        term: { type: "IRI", iri: "urn:item" },
        untouched: { type: "unknown", value: "kept" },
      }),
    );

    expect(request).toEqual({
      term: { type: "IRI", iri: "urn:item" },
      malformedKnownTag: { t: "i" },
      untouched: { t: "unknown", value: "kept" },
    });
    expect(response).toEqual({
      term: { t: "i", i: "urn:item" },
      untouched: { type: "unknown", value: "kept" },
    });
  });

  it("caches Effect requestors as scoped handles", async () => {
    const backend = new DispatchBackend();
    const manager = makeDispatcherManager({
      port: 0,
      metricsPort: 0,
      pubsub: backend,
    });

    await Effect.runPromise(manager.start);
    const first = await Effect.runPromise(manager.dispatchGlobalService("config", { operation: "get" }));
    const second = await Effect.runPromise(manager.dispatchGlobalService("config", { operation: "list" }));
    await Effect.runPromise(manager.stop);

    expect(first).toEqual({ ok: true, echo: { operation: "get" } });
    expect(second).toEqual({ ok: true, echo: { operation: "list" } });
    expect(backend.producerOptions.filter((options) => options.topic === "tg.flow.config-request")).toHaveLength(1);
    expect(backend.consumerOptions.filter((options) => options.topic === "tg.flow.config-response")).toHaveLength(1);
    expect(backend.producersByTopic.get("tg.flow.config-request")?.closeCount).toBe(1);
    expect(backend.consumersByTopic.get("tg.flow.config-response")?.closeCount).toBe(1);
    expect(backend.closeCount).toBe(0);
  });

  it("serializes concurrent requestor creation for the same service", async () => {
    const backend = new DispatchBackend();
    const manager = makeDispatcherManager({
      port: 0,
      metricsPort: 0,
      pubsub: backend,
    });

    await Effect.runPromise(manager.start);
    const [first, second] = await Effect.runPromise(Effect.all([
      manager.dispatchGlobalService("config", { operation: "get" }),
      manager.dispatchGlobalService("config", { operation: "list" }),
    ], { concurrency: "unbounded" }));
    await Effect.runPromise(manager.stop);

    expect(first).toEqual({ ok: true, echo: { operation: "get" } });
    expect(second).toEqual({ ok: true, echo: { operation: "list" } });
    expect(backend.producerOptions.filter((options) => options.topic === "tg.flow.config-request")).toHaveLength(1);
    expect(backend.consumerOptions.filter((options) => options.topic === "tg.flow.config-response")).toHaveLength(1);
  });

  it("does not start requestors when request serialization fails", async () => {
    const backend = new DispatchBackend();
    const manager = makeDispatcherManager({
      port: 0,
      metricsPort: 0,
      pubsub: backend,
    });

    await expect(
      Effect.runPromise(manager.dispatchGlobalService("knowledge", { term: { t: "t" } })),
    ).rejects.toMatchObject({
      _tag: "DispatchSerializationError",
      operation: "client-term-to-internal",
    });
    await Effect.runPromise(manager.stop);

    expect(backend.producerOptions).toHaveLength(0);
    expect(backend.consumerOptions).toHaveLength(0);
    expect(backend.closeCount).toBe(0);
  });

  it("closes one-shot publish producers when send fails", async () => {
    const backend = new DispatchBackend();
    backend.failSendTopics.add("tg.flow.ingest");
    const manager = makeDispatcherManager({
      port: 0,
      metricsPort: 0,
      pubsub: backend,
    });

    await expect(
      Effect.runPromise(manager.publishToTopic("tg.flow.ingest", { text: "hello" }, "msg-1")),
    ).rejects.toMatchObject({
      _tag: "MessagingDeliveryError",
      operation: "send",
    });
    await Effect.runPromise(manager.stop);

    expect(backend.producersByTopic.get("tg.flow.ingest")?.closeCount).toBe(1);
    expect(backend.closeCount).toBe(0);
  });

  it("streams responses until the centralized completion predicate is true", async () => {
    const backend = new DispatchBackend();
    const manager = makeDispatcherManager({
      port: 0,
      metricsPort: 0,
      pubsub: backend,
    });
    const chunks: Array<{ readonly response: unknown; readonly complete: boolean }> = [];

    await Effect.runPromise(
      manager.dispatchGlobalServiceStreaming("knowledge", { query: "hello" }, (response, complete) =>
        Effect.sync(() => {
          chunks.push({ response, complete });
        })
      ),
    );
    await Effect.runPromise(manager.stop);

    expect(chunks).toEqual([
      { response: { chunk: 1 }, complete: false },
      { response: { chunk: 2, endOfStream: true }, complete: true },
    ]);
  });

  it("streams responses through the Effect-native responder path", async () => {
    const backend = new DispatchBackend();
    const manager = makeDispatcherManager({
      port: 0,
      metricsPort: 0,
      pubsub: backend,
    });
    const chunks: Array<{ readonly response: unknown; readonly complete: boolean }> = [];

    await Effect.runPromise(
      manager.dispatchGlobalServiceStreaming("knowledge", { query: "hello" }, (response, complete) =>
        Effect.sync(() => {
          chunks.push({ response, complete });
        })
      ),
    );
    await Effect.runPromise(manager.stop);

    expect(chunks).toEqual([
      { response: { chunk: 1 }, complete: false },
      { response: { chunk: 2, endOfStream: true }, complete: true },
    ]);
  });

  it.each([
    [{ complete: true }],
    [{ endOfStream: true }],
    [{ endOfSession: true }],
    [{ end_of_stream: true }],
    [{ end_of_session: true }],
    [{ end_of_dialog: true }],
    [{ eos: true }],
    [{ error: { message: "failed" } }],
    ["plain"],
    [null],
  ])("treats %j as a complete streaming response", (response) => {
    expect(dispatcherManagerIsCompleteResponse(response)).toBe(true);
  });

  it("does not mark ordinary response objects complete", () => {
    expect(dispatcherManagerIsCompleteResponse({ chunk: 1 })).toBe(false);
  });
});
