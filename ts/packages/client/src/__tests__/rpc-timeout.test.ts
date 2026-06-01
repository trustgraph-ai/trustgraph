import { Effect, Stream } from "effect";
import { describe, expect, it, vi } from "vitest";
import { DispatchError, DispatchStreamChunk } from "../rpc/contract";
import { EffectRpcClient, type DispatchInput } from "../socket/effect-rpc-client";
import { BaseApi } from "../socket/trustgraph-socket";

const input: DispatchInput = {
  scope: "global",
  service: "config",
  request: { operation: "list" },
};

describe("Effect RPC request policy", () => {
  it("threads BaseApi timeout and retry options into dispatch calls", async () => {
    const dispatch = vi.fn(() => Promise.resolve({ ok: true }));
    const api = Object.create(BaseApi.prototype) as BaseApi;

    (api as unknown as { rpc: { dispatch: typeof dispatch } }).rpc = {
      dispatch,
    };

    await api.makeRequest("config", { operation: "list" }, 25, 2);

    expect(dispatch).toHaveBeenCalledWith(input, {
      timeoutMs: 25,
      retries: 2,
    });
  });

  it("rejects stalled dispatch calls at the requested timeout", async () => {
    const client = Object.create(EffectRpcClient.prototype) as EffectRpcClient;
    const startedAt = Date.now();

    setClientPromise(client, {
      Dispatch: () => Effect.never,
      DispatchStream: () => Stream.never,
    });

    await expect(
      client.dispatch(input, { timeoutMs: 20, retries: 1 }),
    ).rejects.toBeInstanceOf(DispatchError);

    expect(Date.now() - startedAt).toBeLessThan(1_000);
  });

  it("retries dispatch failures up to the requested attempt count", async () => {
    const client = Object.create(EffectRpcClient.prototype) as EffectRpcClient;
    let attempts = 0;

    setClientPromise(client, {
      Dispatch: () =>
        Effect.suspend(() => {
          attempts += 1;
          if (attempts < 3) {
            return Effect.fail(new DispatchError({ message: String(attempts) }));
          }
          return Effect.succeed({ ok: true });
        }),
      DispatchStream: () => Stream.never,
    });

    await expect(client.dispatch(input, { timeoutMs: 100, retries: 3 })).resolves.toEqual({
      ok: true,
    });

    expect(attempts).toBe(3);
  });
});

function setClientPromise(
  client: EffectRpcClient,
  fakeClient: {
    Dispatch: (payload: unknown) => Effect.Effect<unknown, DispatchError>;
    DispatchStream: (payload: unknown) => Stream.Stream<DispatchStreamChunk, DispatchError>;
  },
): void {
  (client as unknown as { clientPromise: Promise<typeof fakeClient> }).clientPromise =
    Promise.resolve(fakeClient);
}
