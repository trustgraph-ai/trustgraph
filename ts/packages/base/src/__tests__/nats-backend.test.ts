import { beforeEach, describe, expect, it, vi } from "vitest";
import { makeNatsBackend } from "../backend/nats.js";

const natsMock = vi.hoisted(() => {
  const S = require("effect/Schema");
  const encoder = new TextEncoder();
  const decoder = new TextDecoder();

  class MockNatsError extends S.TaggedErrorClass()(
    "MockNatsError",
    {
      apiCode: S.optional(S.Number),
      code: S.String,
      message: S.String,
    },
  ) {
    constructor(code: string, apiCode?: number) {
      super({
        apiCode,
        code,
        message: code,
      });
    }

    jsError() {
      return this.apiCode === undefined
        ? null
        : {
            code: this.apiCode,
            description: this.code,
          };
    }
  }

  const publish = vi.fn();
  const consumersGet = vi.fn();
  const consumersAdd = vi.fn();
  const streamsInfo = vi.fn();
  const streamsAdd = vi.fn();
  const next = vi.fn();
  const ack = vi.fn();
  const nak = vi.fn();
  const drain = vi.fn();
  const headerAppend = vi.fn();
  const headers = vi.fn();
  const connect = vi.fn();

  return {
    ack,
    connect,
    consumersAdd,
    consumersGet,
    decoder,
    drain,
    encoder,
    headerAppend,
    headers,
    NatsError: MockNatsError,
    nak,
    next,
    publish,
    streamsAdd,
    streamsInfo,
  };
});

vi.mock("nats", () => ({
  AckPolicy: { Explicit: "explicit" },
  DeliverPolicy: { All: "all", New: "new" },
  ErrorCode: { JetStream404NoMessages: "404" },
  StringCodec: () => ({
    decode: (input: Uint8Array) => natsMock.decoder.decode(input),
    encode: (input: string) => natsMock.encoder.encode(input),
  }),
  connect: natsMock.connect,
  headers: natsMock.headers,
  NatsError: natsMock.NatsError,
}));

function makeNatsError(code: string, apiCode?: number) {
  return new natsMock.NatsError(code, apiCode);
}

function resetNatsMock(): void {
  vi.clearAllMocks();

  natsMock.publish.mockResolvedValue({ duplicate: false, seq: 1, stream: "tg_test" });
  natsMock.consumersGet.mockResolvedValue({ next: natsMock.next });
  natsMock.consumersAdd.mockResolvedValue(undefined);
  natsMock.streamsInfo.mockResolvedValue({ config: { name: "tg_test" } });
  natsMock.streamsAdd.mockResolvedValue(undefined);
  natsMock.next.mockResolvedValue({
    ack: natsMock.ack,
    data: natsMock.encoder.encode(JSON.stringify("payload")),
    headers: undefined,
    nak: natsMock.nak,
  });
  natsMock.ack.mockReturnValue(undefined);
  natsMock.nak.mockReturnValue(undefined);
  natsMock.drain.mockResolvedValue(undefined);
  natsMock.headerAppend.mockReturnValue(undefined);
  natsMock.headers.mockReturnValue({ append: natsMock.headerAppend });
  natsMock.connect.mockResolvedValue({
    drain: natsMock.drain,
    jetstream: () => ({
      consumers: { get: natsMock.consumersGet },
      publish: natsMock.publish,
    }),
    jetstreamManager: () =>
      Promise.resolve({
        consumers: { add: natsMock.consumersAdd },
        streams: {
          add: natsMock.streamsAdd,
          info: natsMock.streamsInfo,
        },
      }),
  });
}

describe("NATS backend", () => {
  beforeEach(() => {
    resetNatsMock();
  });

  it("creates streams only when stream lookup returns a JetStream 404", async () => {
    natsMock.streamsInfo.mockRejectedValueOnce(makeNatsError("404", 404));
    const backend = makeNatsBackend("nats://test");

    await backend.createProducer<string>({ topic: "tg.test.topic" });

    expect(natsMock.streamsAdd).toHaveBeenCalledWith({
      name: "tg_test",
      subjects: ["tg.test.>"],
    });
  });

  it("caches initialized streams through the Effect mutable set", async () => {
    const backend = makeNatsBackend("nats://test");

    await backend.createProducer<string>({ topic: "tg.test.topic" });
    await backend.createConsumer<string>({
      topic: "tg.test.other",
      subscription: "worker",
    });

    expect(natsMock.streamsInfo).toHaveBeenCalledTimes(1);
    expect(natsMock.streamsInfo).toHaveBeenCalledWith("tg_test");
  });

  it("does not create streams for non-missing lookup failures", async () => {
    natsMock.streamsInfo.mockRejectedValueOnce(makeNatsError("PERMISSIONS_VIOLATION"));
    const backend = makeNatsBackend("nats://test");

    const error = await backend.createProducer<string>({ topic: "tg.test.topic" }).catch((caught: unknown) => caught);

    expect(error).toMatchObject({
      _tag: "PubSubError",
      operation: "stream-info:tg_test",
    });
    expect(natsMock.streamsAdd).not.toHaveBeenCalled();
  });

  it("creates durable consumers only when consumer lookup returns a JetStream 404", async () => {
    natsMock.consumersGet
      .mockRejectedValueOnce(makeNatsError("404", 404))
      .mockResolvedValueOnce({ next: natsMock.next });
    const backend = makeNatsBackend("nats://test");

    await backend.createConsumer<string>({
      topic: "tg.test.topic",
      subscription: "worker",
    });

    expect(natsMock.consumersAdd).toHaveBeenCalledWith("tg_test", {
      ack_policy: "explicit",
      deliver_policy: "new",
      durable_name: "worker",
      filter_subject: "tg.test.topic",
    });
  });

  it("does not create durable consumers for non-missing lookup failures", async () => {
    natsMock.consumersGet.mockRejectedValueOnce(makeNatsError("PERMISSIONS_VIOLATION"));
    const backend = makeNatsBackend("nats://test");

    const error = await backend.createConsumer<string>({
      topic: "tg.test.topic",
      subscription: "worker",
    }).catch((caught: unknown) => caught);

    expect(error).toMatchObject({
      _tag: "PubSubError",
      operation: "init-consumer:tg.test.topic",
    });
    expect(natsMock.consumersAdd).not.toHaveBeenCalled();
  });

  it("maps invalid publish headers to tagged PubSubError", async () => {
    natsMock.headerAppend.mockImplementation(() => {
      throw "invalid header";
    });
    const backend = makeNatsBackend("nats://test");
    const producer = await backend.createProducer<string>({ topic: "tg.test.topic" });

    const error = await producer.send("hello", { bad: "value" }).catch((caught: unknown) => caught);

    expect(error).toMatchObject({
      _tag: "PubSubError",
      operation: "headers:tg.test.topic",
    });
    expect(natsMock.publish).not.toHaveBeenCalled();
  });

  it("maps thrown ack and nak failures to tagged PubSubError", async () => {
    natsMock.ack.mockImplementation(() => {
      throw "ack failed";
    });
    natsMock.nak.mockImplementation(() => {
      throw "nak failed";
    });
    const backend = makeNatsBackend("nats://test");
    const consumer = await backend.createConsumer<string>({
      topic: "tg.test.topic",
      subscription: "worker",
    });
    const message = await consumer.receive(1);

    expect(message).not.toBeNull();
    if (message === null) {
      return;
    }

    const ackError = await consumer.acknowledge(message).catch((caught: unknown) => caught);
    const nakError = await consumer.negativeAcknowledge(message).catch((caught: unknown) => caught);

    expect(ackError).toMatchObject({
      _tag: "PubSubError",
      operation: "acknowledge:tg.test.topic",
    });
    expect(nakError).toMatchObject({
      _tag: "PubSubError",
      operation: "negative-acknowledge:tg.test.topic",
    });
  });
});
