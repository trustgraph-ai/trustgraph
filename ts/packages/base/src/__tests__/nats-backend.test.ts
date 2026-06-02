import { beforeEach, describe, expect, it, vi } from "vitest";
import { makeNatsBackend } from "../backend/nats.js";

const natsMock = vi.hoisted(() => {
  const encoder = new TextEncoder();
  const decoder = new TextDecoder();

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
  StringCodec: () => ({
    decode: (input: Uint8Array) => natsMock.decoder.decode(input),
    encode: (input: string) => natsMock.encoder.encode(input),
  }),
  connect: natsMock.connect,
  headers: natsMock.headers,
}));

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
