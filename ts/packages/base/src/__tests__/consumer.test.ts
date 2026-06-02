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
    });

    expect(consumer).toMatchObject({
      start: expect.any(Function),
      stop: expect.any(Function),
    });
  });

  // ── start() creates consumer and calls handler ─────────────────
  it("creates a backend consumer and invokes handler for received messages", async () => {
    const handler = vi.fn().mockResolvedValue(undefined);
    const msg = createMockMessage({ data: "hello" }, { id: "1" });

    // First call returns a message, second call triggers stop
    let callCount = 0;
    backendConsumer.receive.mockImplementation(async () => {
      callCount++;
      if (callCount === 1) return msg;
      // Stop the consumer on second receive
      await consumer.stop();
      return null;
    });

    const consumer = makeConsumer({
      pubsub,
      topic: "topic-a",
      subscription: "sub-a",
      handler,
    });

    // start() blocks until the consume loop ends, so we don't need to await separately
    await consumer.start(flowCtx);

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

    let callCount = 0;
    backendConsumer.receive.mockImplementation(async () => {
      callCount++;
      if (callCount === 1) return msg;
      await consumer.stop();
      return null;
    });

    const consumer = makeConsumer({
      pubsub,
      topic: "t",
      subscription: "s",
      handler,
    });

    await consumer.start(flowCtx);

    expect(backendConsumer.acknowledge).toHaveBeenCalledWith(msg);
    expect(backendConsumer.negativeAcknowledge).not.toHaveBeenCalled();
  });

  // ── Messages are negatively acknowledged on handler error ──────
  it("negatively acknowledges messages when the handler throws", async () => {
    const handler = vi.fn().mockRejectedValue(new Error("handler boom"));
    const msg = createMockMessage("bad-payload");

    let callCount = 0;
    backendConsumer.receive.mockImplementation(async () => {
      callCount++;
      if (callCount === 1) return msg;
      // Stop on second call (after the 1s sleep from error handling)
      await consumer.stop();
      return null;
    });

    const consumer = makeConsumer({
      pubsub,
      topic: "t",
      subscription: "s",
      handler,
    });

    // Suppress console.error noise
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    // start() will block; the error path sleeps 1s, so we need to advance timers
    const startPromise = consumer.start(flowCtx);
    // Advance past the 1s sleep in the error handler
    await vi.advanceTimersByTimeAsync(1500);
    await startPromise;

    expect(backendConsumer.negativeAcknowledge).toHaveBeenCalledWith(msg);
    expect(backendConsumer.acknowledge).not.toHaveBeenCalled();

    errorSpy.mockRestore();
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

    let receiveCount = 0;
    backendConsumer.receive.mockImplementation(async () => {
      receiveCount++;
      if (receiveCount === 1) return msg;
      await consumer.stop();
      return null;
    });

    const consumer = makeConsumer({
      pubsub,
      topic: "t",
      subscription: "s",
      handler,
      rateLimitRetryMs: 500,
    });

    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});

    const startPromise = consumer.start(flowCtx);
    // Advance past the rate-limit retry delay (500ms)
    await vi.advanceTimersByTimeAsync(600);
    await startPromise;

    // Handler called twice: first throws TooManyRequestsError, second succeeds
    expect(handler).toHaveBeenCalledTimes(2);
    // Message should be acknowledged (retry succeeded)
    expect(backendConsumer.acknowledge).toHaveBeenCalledWith(msg);

    warnSpy.mockRestore();
  });

  // ── stop() closes the backend ──────────────────────────────────
  it("stop() sets running=false and closes the backend", async () => {
    // Make receive block forever (returns null) until stopped
    backendConsumer.receive.mockImplementation(async () => {
      // Yield control so stop() can run
      await new Promise((r) => setTimeout(r, 100));
      return null;
    });

    const consumer = makeConsumer({
      pubsub,
      topic: "t",
      subscription: "s",
      handler: vi.fn(),
    });

    const startPromise = consumer.start(flowCtx);

    // Advance timers to let the consume loop iterate once
    await vi.advanceTimersByTimeAsync(200);

    await consumer.stop();

    // Advance timers further so the loop can exit
    await vi.advanceTimersByTimeAsync(200);
    await startPromise;

    expect(backendConsumer.close).toHaveBeenCalled();
    await expect(consumer.stop()).resolves.toBeUndefined();
  });
});
