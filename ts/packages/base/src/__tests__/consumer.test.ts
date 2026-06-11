import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { Effect } from "effect";
import type { FlowContext } from "../messaging/consumer.js";
import { makeConsumer, } from "../messaging/consumer.js";
import type {
  PubSubBackend,
  BackendConsumer,
  Message,
  BackendProducer,
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
  close: Effect.Effect<void>;
  closeMock: ReturnType<typeof vi.fn>;
} {
  const closeMock = vi.fn();
  return {
    receive: vi.fn().mockReturnValue(Effect.succeed(null)),
    acknowledge: vi.fn().mockReturnValue(Effect.void),
    negativeAcknowledge: vi.fn().mockReturnValue(Effect.void),
    unsubscribe: vi.fn().mockReturnValue(Effect.void),
    close: Effect.sync(closeMock),
    closeMock,
  };
}

// ── Mock PubSubBackend ───────────────────────────────────────────────
function createMockPubSub<T>(
  backendConsumer: BackendConsumer<T>,
): PubSubBackend {
  return {
    createProducer: vi.fn().mockReturnValue(Effect.succeed({} as BackendProducer<unknown>)),
    createConsumer: vi.fn().mockReturnValue(Effect.succeed(backendConsumer)),
    close: Effect.void,
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
      stop: expect.any(Object),
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
      stop: expect.any(Object),
    });
  });

  // ── start() creates consumer and calls handler ─────────────────
  it("starts a scoped consumer and invokes handler for received messages", async () => {
    const handler = vi.fn().mockReturnValue(Effect.void);
    const msg = createMockMessage({ data: "hello" }, { id: "1" });

    const consumer = makeConsumer({
      pubsub,
      topic: "topic-a",
      subscription: "sub-a",
      handler,
    });

    backendConsumer.receive.mockReturnValueOnce(Effect.succeed(msg)).mockReturnValue(Effect.succeed(null));

    await Effect.runPromise(consumer.start(flowCtx));
    await advanceUntil(() => handler.mock.calls.length > 0);
    await Effect.runPromise(consumer.stop);

    expect(pubsub.createConsumer).toHaveBeenCalledWith({
      topic: "topic-a",
      subscription: "sub-a",
      initialPosition: "latest",
    });
    expect(handler).toHaveBeenCalledWith({ data: "hello" }, { id: "1" }, flowCtx);
  });

  // ── Messages are acknowledged after successful handling ────────
  it("acknowledges messages after successful handling", async () => {
    const handler = vi.fn().mockReturnValue(Effect.void);
    const msg = createMockMessage("payload");

    const consumer = makeConsumer({
      pubsub,
      topic: "t",
      subscription: "s",
      handler,
    });

    backendConsumer.receive.mockReturnValueOnce(Effect.succeed(msg)).mockReturnValue(Effect.succeed(null));

    await Effect.runPromise(consumer.start(flowCtx));
    await advanceUntil(() => backendConsumer.acknowledge.mock.calls.length > 0);
    await Effect.runPromise(consumer.stop);

    expect(backendConsumer.acknowledge).toHaveBeenCalledWith(msg);
    expect(backendConsumer.negativeAcknowledge).not.toHaveBeenCalled();
  });

  // ── Messages are negatively acknowledged on handler error ──────
  it("negatively acknowledges messages when the handler throws", async () => {
    const handler = vi.fn().mockReturnValue(Effect.fail("handler boom"));
    const msg = createMockMessage("bad-payload");

    const consumer = makeConsumer({
      pubsub,
      topic: "t",
      subscription: "s",
      handler,
    });

    backendConsumer.receive.mockReturnValueOnce(Effect.succeed(msg)).mockReturnValue(Effect.succeed(null));

    await Effect.runPromise(consumer.start(flowCtx));
    await advanceUntil(() => backendConsumer.negativeAcknowledge.mock.calls.length > 0);
    await Effect.runPromise(consumer.stop);

    expect(backendConsumer.negativeAcknowledge).toHaveBeenCalledWith(msg);
    expect(backendConsumer.acknowledge).not.toHaveBeenCalled();
  });

  // ── TooManyRequestsError triggers retry ────────────────────────
  it("retries the handler on TooManyRequestsError", async () => {
    let handlerCalls = 0;
    const handler = vi.fn().mockImplementation(() => {
      return Effect.sync(() => {
        handlerCalls++;
        return handlerCalls;
      }).pipe(
        Effect.flatMap((attempt) =>
          attempt === 1
            ? Effect.fail(tooManyRequestsError("rate limited"))
            : Effect.void
        ),
      );
    });

    const msg = createMockMessage("rate-limited-payload");

    const consumer = makeConsumer({
      pubsub,
      topic: "t",
      subscription: "s",
      handler,
      rateLimitRetryMs: 500,
    });

    backendConsumer.receive.mockReturnValueOnce(Effect.succeed(msg)).mockReturnValue(Effect.succeed(null));

    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});

    await Effect.runPromise(consumer.start(flowCtx));
    await vi.advanceTimersByTimeAsync(600);
    await advanceUntil(() => handler.mock.calls.length >= 2);
    await Effect.runPromise(consumer.stop);

    // Handler called twice: first throws TooManyRequestsError, second succeeds
    expect(handlerCalls).toBe(2);
    // Message should be acknowledged (retry succeeded)
    expect(backendConsumer.acknowledge).toHaveBeenCalledWith(msg);

    warnSpy.mockRestore();
  });

  it("retries repeated TooManyRequestsError until success within the timeout", async () => {
    let handlerCalls = 0;
    const handler = vi.fn().mockImplementation(() => {
      return Effect.sync(() => {
        handlerCalls++;
        return handlerCalls;
      }).pipe(
        Effect.flatMap((attempt) =>
          attempt <= 2
            ? Effect.fail(tooManyRequestsError("rate limited"))
            : Effect.void
        ),
      );
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

    backendConsumer.receive.mockReturnValueOnce(Effect.succeed(msg)).mockReturnValue(Effect.succeed(null));

    await Effect.runPromise(consumer.start(flowCtx));
    await vi.advanceTimersByTimeAsync(1_100);
    await advanceUntil(() => backendConsumer.acknowledge.mock.calls.length > 0);
    await Effect.runPromise(consumer.stop);

    expect(handlerCalls).toBe(3);
    expect(backendConsumer.acknowledge).toHaveBeenCalledWith(msg);
    expect(backendConsumer.negativeAcknowledge).not.toHaveBeenCalled();
  });

  it("negatively acknowledges when rate-limit retry timeout elapses", async () => {
    let handlerCalls = 0;
    const handler = vi.fn().mockReturnValue(
      Effect.sync(() => {
        handlerCalls++;
      }).pipe(
        Effect.flatMap(() => Effect.fail(tooManyRequestsError("rate limited"))),
      ),
    );
    const msg = createMockMessage("rate-limited-payload");

    const consumer = makeConsumer({
      pubsub,
      topic: "t",
      subscription: "s",
      handler,
      rateLimitRetryMs: 500,
      rateLimitTimeoutMs: 1_000,
    });

    backendConsumer.receive.mockReturnValueOnce(Effect.succeed(msg)).mockReturnValue(Effect.succeed(null));

    await Effect.runPromise(consumer.start(flowCtx));
    await vi.advanceTimersByTimeAsync(1_100);
    await advanceUntil(() => backendConsumer.negativeAcknowledge.mock.calls.length > 0);
    await Effect.runPromise(consumer.stop);

    expect(handlerCalls).toBeGreaterThanOrEqual(2);
    expect(backendConsumer.negativeAcknowledge).toHaveBeenCalledWith(msg);
    expect(backendConsumer.acknowledge).not.toHaveBeenCalled();
  });

  // ── stop() closes the backend ──────────────────────────────────
  it("stop() sets running=false and closes the backend", async () => {
    backendConsumer.receive.mockReturnValue(Effect.succeed(null));

    const consumer = makeConsumer({
      pubsub,
      topic: "t",
      subscription: "s",
      handler: vi.fn(),
    });

    await Effect.runPromise(consumer.start(flowCtx));
    await Effect.runPromise(consumer.stop);

    expect(backendConsumer.closeMock).toHaveBeenCalled();
    await expect(Effect.runPromise(consumer.stop)).resolves.toBeUndefined();
  });
});
