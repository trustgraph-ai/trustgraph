import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { makeConsumer, type ConsumerOptions, type FlowContext } from "../messaging/consumer.js";
import type {
  PubSubBackend,
  BackendConsumer,
  Message,
  BackendProducer,
  CreateProducerOptions,
  CreateConsumerOptions,
} from "../backend/types.js";
import { tooManyRequestsError } from "../errors.js";
import type { Flow } from "../processor/flow.js";

// ── Mock Message ──────────────────────────────────────────────────────
function createMockMessage<T>(val: T, props: Record<string, string> = {}): Message<T> {
  return {
    value: () => val,
    properties: () => props,
  };
}

// ── Mock BackendConsumer ──────────────────────────────────────────────
function createMockBackendConsumer<T>(): BackendConsumer<T> & {
  receive: ReturnType<typeof vi.fn>;
  acknowledge: ReturnType<typeof vi.fn>;
  negativeAcknowledge: ReturnType<typeof vi.fn>;
  unsubscribe: ReturnType<typeof vi.fn>;
  close: ReturnType<typeof vi.fn>;
} {
  return {
    receive: vi.fn().mockResolvedValue(null),
    acknowledge: vi.fn().mockResolvedValue(undefined),
    negativeAcknowledge: vi.fn().mockResolvedValue(undefined),
    unsubscribe: vi.fn().mockResolvedValue(undefined),
    close: vi.fn().mockResolvedValue(undefined),
  };
}

// ── Mock PubSubBackend ───────────────────────────────────────────────
function createMockPubSub<T>(
  backendConsumer: BackendConsumer<T>,
): PubSubBackend {
  return {
    createProducer: vi.fn().mockResolvedValue({} as BackendProducer<unknown>),
    createConsumer: vi.fn().mockResolvedValue(backendConsumer),
    close: vi.fn().mockResolvedValue(undefined),
  };
}

// ── Minimal FlowContext stub ─────────────────────────────────────────
function createFlowContext(): FlowContext {
  return {
    id: "test-flow-id",
    name: "test-flow",
    flow: {} as Flow,
  };
}

async function advanceUntil(
  predicate: () => boolean,
  totalMs = 1_000,
  stepMs = 10,
): Promise<void> {
  for (let elapsed = 0; elapsed < totalMs && !predicate(); elapsed += stepMs) {
    await vi.advanceTimersByTimeAsync(stepMs);
  }
}

describe("Consumer", () => {
  let backendConsumer: ReturnType<typeof createMockBackendConsumer>;
  let pubsub: PubSubBackend;
  let flowCtx: FlowContext;

  beforeEach(() => {
    backendConsumer = createMockBackendConsumer();
    pubsub = createMockPubSub(backendConsumer);
    flowCtx = createFlowContext();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  // ── Constructor ──────────────────────────────────────────────────
  it("stores options and applies defaults", () => {
    const handler = vi.fn();
    const consumer = makeConsumer({
      pubsub,
      topic: "my-topic",
      subscription: "my-sub",
      handler,
    });

    expect(consumer).toMatchObject({
      start: expect.any(Function),
      stop: expect.any(Function),
    });
  });

  it("accepts custom concurrency and rateLimitRetryMs", () => {
    const consumer = makeConsumer({
      pubsub,
      topic: "t",
      subscription: "s",
      handler: vi.fn(),
      concurrency: 4,
      rateLimitRetryMs: 5_000,
      rateLimitTimeoutMs: 10_000,
    });

    expect(consumer).toMatchObject({
      start: expect.any(Function),
      stop: expect.any(Function),
    });
  });

  // ── start() creates consumer and calls handler ─────────────────
  it("starts a scoped consumer and invokes handler for received messages", async () => {
    const handler = vi.fn().mockResolvedValue(undefined);
    const msg = createMockMessage({ data: "hello" }, { id: "1" });

    const consumer = makeConsumer({
      pubsub,
      topic: "topic-a",
      subscription: "sub-a",
      handler,
    });

    backendConsumer.receive.mockResolvedValueOnce(msg).mockResolvedValue(null);

    await consumer.start(flowCtx);
    await advanceUntil(() => handler.mock.calls.length > 0);
    await consumer.stop();

    expect(pubsub.createConsumer).toHaveBeenCalledWith({
      topic: "topic-a",
      subscription: "sub-a",
      initialPosition: "latest",
    });
    expect(handler).toHaveBeenCalledWith({ data: "hello" }, { id: "1" }, flowCtx);
  });

  // ── Messages are acknowledged after successful handling ────────
  it("acknowledges messages after successful handling", async () => {
    const handler = vi.fn().mockResolvedValue(undefined);
    const msg = createMockMessage("payload");

    const consumer = makeConsumer({
      pubsub,
      topic: "t",
      subscription: "s",
      handler,
    });

    backendConsumer.receive.mockResolvedValueOnce(msg).mockResolvedValue(null);

    await consumer.start(flowCtx);
    await advanceUntil(() => backendConsumer.acknowledge.mock.calls.length > 0);
    await consumer.stop();

    expect(backendConsumer.acknowledge).toHaveBeenCalledWith(msg);
    expect(backendConsumer.negativeAcknowledge).not.toHaveBeenCalled();
  });

  // ── Messages are negatively acknowledged on handler error ──────
  it("negatively acknowledges messages when the handler throws", async () => {
    const handler = vi.fn().mockRejectedValue("handler boom");
    const msg = createMockMessage("bad-payload");

    const consumer = makeConsumer({
      pubsub,
      topic: "t",
      subscription: "s",
      handler,
    });

    backendConsumer.receive.mockResolvedValueOnce(msg).mockResolvedValue(null);

    await consumer.start(flowCtx);
    await advanceUntil(() => backendConsumer.negativeAcknowledge.mock.calls.length > 0);
    await consumer.stop();

    expect(backendConsumer.negativeAcknowledge).toHaveBeenCalledWith(msg);
    expect(backendConsumer.acknowledge).not.toHaveBeenCalled();
  });

  // ── TooManyRequestsError triggers retry ────────────────────────
  it("retries the handler on TooManyRequestsError", async () => {
    let handlerCalls = 0;
    const handler = vi.fn().mockImplementation(async () => {
      handlerCalls++;
      if (handlerCalls === 1) {
        throw tooManyRequestsError("rate limited");
      }
      // Second call succeeds
    });

    const msg = createMockMessage("rate-limited-payload");

    const consumer = makeConsumer({
      pubsub,
      topic: "t",
      subscription: "s",
      handler,
      rateLimitRetryMs: 500,
    });

    backendConsumer.receive.mockResolvedValueOnce(msg).mockResolvedValue(null);

    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});

    await consumer.start(flowCtx);
    await vi.advanceTimersByTimeAsync(600);
    await advanceUntil(() => handler.mock.calls.length >= 2);
    await consumer.stop();

    // Handler called twice: first throws TooManyRequestsError, second succeeds
    expect(handler).toHaveBeenCalledTimes(2);
    // Message should be acknowledged (retry succeeded)
    expect(backendConsumer.acknowledge).toHaveBeenCalledWith(msg);

    warnSpy.mockRestore();
  });

  it("retries repeated TooManyRequestsError until success within the timeout", async () => {
    let handlerCalls = 0;
    const handler = vi.fn().mockImplementation(async () => {
      handlerCalls++;
      if (handlerCalls <= 2) {
        throw tooManyRequestsError("rate limited");
      }
    });

    const msg = createMockMessage("rate-limited-payload");

    const consumer = makeConsumer({
      pubsub,
      topic: "t",
      subscription: "s",
      handler,
      rateLimitRetryMs: 500,
      rateLimitTimeoutMs: 2_000,
    });

    backendConsumer.receive.mockResolvedValueOnce(msg).mockResolvedValue(null);

    await consumer.start(flowCtx);
    await vi.advanceTimersByTimeAsync(1_100);
    await advanceUntil(() => backendConsumer.acknowledge.mock.calls.length > 0);
    await consumer.stop();

    expect(handler).toHaveBeenCalledTimes(3);
    expect(backendConsumer.acknowledge).toHaveBeenCalledWith(msg);
    expect(backendConsumer.negativeAcknowledge).not.toHaveBeenCalled();
  });

  it("negatively acknowledges when rate-limit retry timeout elapses", async () => {
    const handler = vi.fn().mockImplementation(async () => {
      throw tooManyRequestsError("rate limited");
    });
    const msg = createMockMessage("rate-limited-payload");

    const consumer = makeConsumer({
      pubsub,
      topic: "t",
      subscription: "s",
      handler,
      rateLimitRetryMs: 500,
      rateLimitTimeoutMs: 1_000,
    });

    backendConsumer.receive.mockResolvedValueOnce(msg).mockResolvedValue(null);

    await consumer.start(flowCtx);
    await vi.advanceTimersByTimeAsync(1_100);
    await advanceUntil(() => backendConsumer.negativeAcknowledge.mock.calls.length > 0);
    await consumer.stop();

    expect(handler).toHaveBeenCalledTimes(2);
    expect(backendConsumer.negativeAcknowledge).toHaveBeenCalledWith(msg);
    expect(backendConsumer.acknowledge).not.toHaveBeenCalled();
  });

  // ── stop() closes the backend ──────────────────────────────────
  it("stop() sets running=false and closes the backend", async () => {
    backendConsumer.receive.mockResolvedValue(null);

    const consumer = makeConsumer({
      pubsub,
      topic: "t",
      subscription: "s",
      handler: vi.fn(),
    });

    await consumer.start(flowCtx);
    await consumer.stop();

    expect(backendConsumer.close).toHaveBeenCalled();
    await expect(consumer.stop()).resolves.toBeUndefined();
  });
});
