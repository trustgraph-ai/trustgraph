import { Effect } from "effect";
import { describe, expect, it, vi } from "vitest";
import { DispatchError, DispatchStreamChunk } from "../rpc/contract";
import { type DispatchInput, type RpcConnectionState, withDispatchRequestPolicy } from "../socket/effect-rpc-client";
import { type ConnectionState, makeBaseApiWithRpc } from "../socket/trustgraph-socket";

const input: DispatchInput = {
  scope: "global",
  service: "config",
  request: { operation: "list" },
};

describe("Effect RPC request policy", () => {
  it("replays and updates connection state through the SubscriptionRef-backed bridge", async () => {
    let rpcListener: ((state: RpcConnectionState) => void) | undefined;
    const api = makeBaseApiWithRpc("alice", undefined, "ws://example.test/rpc", {
      dispatch: vi.fn(() => Promise.resolve({ ok: true })),
      dispatchStream: vi.fn(() => Promise.resolve(undefined)),
      close: vi.fn(() => Promise.resolve()),
      subscribe: vi.fn((listener) => {
        rpcListener = listener;
        listener({ status: "connecting" });
        return () => undefined;
      }),
    });
    const observed: ConnectionState[] = [];

    const unsubscribe = api.onConnectionStateChange((state) => {
      observed.push(state);
    });

    expect(observed).toEqual([{ status: "connecting", hasApiKey: false }]);
    const listener = rpcListener;
    expect(listener).toBeDefined();
    if (listener !== undefined) {
      listener({ status: "connected" });
    }
    await Effect.runPromise(Effect.yieldNow);

    expect(observed).toEqual([
      { status: "connecting", hasApiKey: false },
      { status: "unauthenticated", hasApiKey: false },
    ]);

    unsubscribe();
    await Effect.runPromise(Effect.yieldNow);
    if (listener !== undefined) {
      listener({ status: "failed", lastError: "boom" });
    }
    await Effect.runPromise(Effect.yieldNow);

    expect(observed).toEqual([
      { status: "connecting", hasApiKey: false },
      { status: "unauthenticated", hasApiKey: false },
    ]);
  });

  it("threads BaseApi timeout and retry options into dispatch calls", async () => {
    const dispatch = vi.fn(() => Promise.resolve({ ok: true }));
    const api = makeBaseApiWithRpc("alice", undefined, "ws://example.test/rpc", {
      dispatch,
      dispatchStream: vi.fn(() => Promise.resolve(undefined)),
      close: vi.fn(() => Promise.resolve()),
      subscribe: vi.fn(() => () => {}),
    });

    await api.makeRequest("config", { operation: "list" }, 25, 2);

    expect(dispatch).toHaveBeenCalledWith(input, {
      timeoutMs: 25,
      retries: 2,
    });
  });

  it("rejects stalled dispatch calls at the requested timeout", async () => {
    const startedAt = Date.now();

    await expect(
      Effect.runPromise(withDispatchRequestPolicy(Effect.never, { timeoutMs: 20, retries: 1 })),
    ).rejects.toBeInstanceOf(DispatchError);

    expect(Date.now() - startedAt).toBeLessThan(1_000);
  });

  it("retries dispatch failures up to the requested attempt count", async () => {
    let attempts = 0;

    await expect(
      Effect.runPromise(
        withDispatchRequestPolicy(
          Effect.suspend(() => {
            attempts += 1;
            if (attempts < 3) {
              return Effect.fail(new DispatchError({ message: String(attempts) }));
            }
            return Effect.succeed({ ok: true });
          }),
          { timeoutMs: 100, retries: 3 },
        ),
      ),
    ).resolves.toEqual({ ok: true });

    expect(attempts).toBe(3);
  });

  it("forwards normalized stream completion to flow streaming facades", () => {
    const dispatchStream = vi.fn((_input: DispatchInput, receiver: (chunk: DispatchStreamChunk) => boolean) => {
      const firstComplete = receiver(DispatchStreamChunk.make({
        response: { response: "alpha" },
        complete: false,
      }));
      const secondComplete = receiver(DispatchStreamChunk.make({
        response: {
          response: "omega",
          in_token: 1,
          out_token: 2,
          model: "test-model",
        },
        complete: true,
      }));
      return Promise.resolve(
        DispatchStreamChunk.make({
          response: { response: "omega" },
          complete: true,
        }),
      ).then((chunk) => {
        expect(firstComplete).toBe(false);
        expect(secondComplete).toBe(true);
        return chunk;
      });
    });
    const api = makeBaseApiWithRpc("alice", undefined, "ws://example.test/rpc", {
      dispatch: vi.fn(() => Promise.resolve({ ok: true })),
      dispatchStream,
      close: vi.fn(() => Promise.resolve()),
      subscribe: vi.fn(() => () => {}),
    });
    const chunks: Array<{
      readonly chunk: string;
      readonly complete: boolean;
      readonly metadata?: { readonly in_token?: number; readonly out_token?: number; readonly model?: string };
    }> = [];

    api.flow("flow-a").graphRagStreaming(
      "hello",
      (chunk, complete, metadata) => {
        chunks.push(metadata === undefined ? { chunk, complete } : { chunk, complete, metadata });
      },
      () => undefined,
    );

    expect(dispatchStream).toHaveBeenCalledWith(
      {
        scope: "flow",
        service: "graph-rag",
        flow: "flow-a",
        request: {
          query: "hello",
          user: "alice",
          collection: "default",
          streaming: true,
        },
      },
      expect.any(Function),
      { timeoutMs: 60000 },
    );
    expect(chunks).toEqual([
      { chunk: "alpha", complete: false },
      {
        chunk: "omega",
        complete: true,
        metadata: { in_token: 1, out_token: 2, model: "test-model" },
      },
    ]);
  });

  it("dispatches agent stream chunk types through the Match-backed callback mapper", async () => {
    const dispatchStream = vi.fn((_input: DispatchInput, receiver: (chunk: DispatchStreamChunk) => boolean) => {
      const ignoredComplete = receiver(DispatchStreamChunk.make({
        response: { chunk_type: "ignored", content: "skip" },
        complete: false,
      }));
      const thoughtComplete = receiver(DispatchStreamChunk.make({
        response: { chunk_type: "thought", content: "plan", end_of_message: true },
        complete: false,
      }));
      const observationComplete = receiver(DispatchStreamChunk.make({
        response: { chunk_type: "observation", content: "facts", end_of_message: true },
        complete: false,
      }));
      const actionComplete = receiver(DispatchStreamChunk.make({
        response: { chunk_type: "action", content: "lookup" },
        complete: false,
      }));
      const answerComplete = receiver(DispatchStreamChunk.make({
        response: {
          chunk_type: "final-answer",
          content: "done",
          end_of_message: true,
          end_of_dialog: true,
          in_token: 3,
          out_token: 5,
          model: "agent-model",
        },
        complete: true,
      }));

      expect(ignoredComplete).toBe(false);
      expect(thoughtComplete).toBe(false);
      expect(observationComplete).toBe(false);
      expect(actionComplete).toBe(false);
      expect(answerComplete).toBe(true);

      return Promise.resolve(
        DispatchStreamChunk.make({
          response: { response: "done" },
          complete: true,
        }),
      );
    });
    const api = makeBaseApiWithRpc("alice", undefined, "ws://example.test/rpc", {
      dispatch: vi.fn(() => Promise.resolve({ ok: true })),
      dispatchStream,
      close: vi.fn(() => Promise.resolve()),
      subscribe: vi.fn(() => () => {}),
    });
    const think = vi.fn();
    const observe = vi.fn();
    const answer = vi.fn();
    const onError = vi.fn();

    await api.flow("flow-a").agent("hello", think, observe, answer, onError);

    expect(dispatchStream).toHaveBeenCalledWith(
      {
        scope: "flow",
        service: "agent",
        flow: "flow-a",
        request: {
          question: "hello",
          user: "alice",
          collection: "default",
          streaming: true,
        },
      },
      expect.any(Function),
      { timeoutMs: 120000, retries: 2 },
    );
    expect(think).toHaveBeenCalledWith("plan", true, undefined);
    expect(observe).toHaveBeenCalledWith("facts", true, undefined);
    expect(answer).toHaveBeenCalledWith(
      "done",
      true,
      { in_token: 3, out_token: 5, model: "agent-model" },
    );
    expect(onError).not.toHaveBeenCalled();
  });
});
