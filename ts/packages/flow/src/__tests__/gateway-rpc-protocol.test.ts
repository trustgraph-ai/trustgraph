import { Effect, Queue } from "effect";
import * as O from "effect/Option";
import * as RpcMessage from "effect/unstable/rpc/RpcMessage";
import * as RpcSerialization from "effect/unstable/rpc/RpcSerialization";
import * as Socket from "effect/unstable/socket/Socket";
import { describe, expect, it } from "vitest";
import { makeSocketRpcProtocol } from "../gateway/rpc-protocol.js";

interface ReceivedMessage {
  readonly clientId: number;
  readonly message: RpcMessage.FromClientEncoded;
}

interface ProtocolRunResult {
  readonly messages: ReadonlyArray<ReceivedMessage>;
  readonly writes: ReadonlyArray<string | Uint8Array | CloseEvent>;
  readonly clientIds: ReadonlyArray<number>;
}

const jsonFrame = (value: unknown): string => `${JSON.stringify(value)}\n`;

const optionToArray = <A>(value: O.Option<A>): Array<A> =>
  O.match(value, {
    onNone: () => [],
    onSome: (item) => [item],
  });

const runProtocolFrames = (
  frames: ReadonlyArray<string | Uint8Array>,
  headers?: ReadonlyArray<[string, string]>,
  sendResponse?: RpcMessage.FromServerEncoded,
): Promise<ProtocolRunResult> =>
  Effect.runPromise(
    Effect.scoped(
      Effect.gen(function* () {
        const received = yield* Queue.unbounded<ReceivedMessage>();
        const writes: Array<string | Uint8Array | CloseEvent> = [];
        const { onSocket, protocol } = yield* makeSocketRpcProtocol;

        yield* protocol.run((clientId, message) =>
          Queue.offer(received, { clientId, message }).pipe(Effect.asVoid)
        ).pipe(Effect.forkScoped);
        yield* Effect.yieldNow;

        const socket = Socket.make({
          writer: Effect.succeed((chunk) =>
            Effect.sync(() => {
              writes.push(chunk);
            })
          ),
          runRaw: (handler) =>
            Effect.forEach(frames, (frame) =>
              Effect.suspend(() => {
                const result = handler(frame);
                return result === undefined ? Effect.void : result;
              }), { discard: true }),
        });

        yield* onSocket(socket, headers);
        yield* Effect.yieldNow;
        const clientIds = yield* protocol.clientIds;
        if (sendResponse !== undefined) {
          yield* protocol.send(0, sendResponse);
        }

        const first = yield* Queue.poll(received);
        const second = yield* Queue.poll(received);
        const third = yield* Queue.poll(received);

        return {
          messages: [
            ...optionToArray(first),
            ...optionToArray(second),
            ...optionToArray(third),
          ],
          writes,
          clientIds: Array.from(clientIds),
        };
      }).pipe(
        Effect.provideService(RpcSerialization.RpcSerialization, RpcSerialization.ndjson),
      ),
    ),
  );

describe("gateway RPC socket protocol", () => {
  it("validates client request frames and prepends websocket headers", async () => {
    const result = await runProtocolFrames([
      jsonFrame({
        _tag: "Request",
        id: "1",
        tag: "Dispatch",
        payload: {
          scope: "global",
          service: "config",
          request: {},
        },
        headers: [["rpc", "client"]],
      }),
    ], [["socket", "header"]]);

    expect(result.writes).toEqual([]);
    expect(result.messages).toHaveLength(1);

    const received = result.messages[0];
    expect(received).toBeDefined();
    if (received === undefined) return;

    expect(received.clientId).toBe(0);
    expect(received.message._tag).toBe("Request");
    if (received.message._tag !== "Request") return;

    expect(received.message.id).toBe("1");
    expect(received.message.tag).toBe("Dispatch");
    expect(received.message.headers).toEqual([
      ["socket", "header"],
      ["rpc", "client"],
    ]);
  });

  it("validates client control frames without mutating them", async () => {
    const result = await runProtocolFrames([
      jsonFrame({
        _tag: "Ping",
      }),
      jsonFrame({
        _tag: "Ack",
        requestId: "1",
      }),
    ]);

    expect(result.writes).toEqual([]);
    expect(result.messages.map(({ message }) => message._tag)).toEqual(["Ping", "Ack"]);
    expect(result.messages[1]?.message).toEqual({
      _tag: "Ack",
      requestId: "1",
    });
  });

  it("rejects server response envelopes received from the socket", async () => {
    const result = await runProtocolFrames([
      jsonFrame({
        _tag: "Exit",
        requestId: "1",
        exit: {
          _tag: "Success",
          value: { ok: true },
        },
      }),
    ]);

    expect(result.messages).toEqual([]);
    expect(result.writes).toHaveLength(1);
    expect(String(result.writes[0])).toContain("\"_tag\":\"Defect\"");
  });

  it("sends server responses through the registered client", async () => {
    const result = await runProtocolFrames(
      [],
      undefined,
      RpcMessage.ResponseDefectEncoded("server-boom"),
    );

    expect(result.clientIds).toEqual([0]);
    expect(result.writes).toHaveLength(1);
    expect(String(result.writes[0])).toContain("server-boom");
  });
});
