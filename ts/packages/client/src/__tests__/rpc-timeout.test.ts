import { Effect } from "effect";
import { describe, expect, it, vi } from "vitest";
import { DispatchError } from "../rpc/contract";
import { type DispatchInput, withDispatchRequestPolicy } from "../socket/effect-rpc-client";
import { makeBaseApiWithRpc } from "../socket/trustgraph-socket";

const input: DispatchInput = {
  scope: "global",
  service: "config",
  request: { operation: "list" },
};

describe("Effect RPC request policy", () => {
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
});
