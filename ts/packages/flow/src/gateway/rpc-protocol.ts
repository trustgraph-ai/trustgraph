import { Effect, Queue, Scope } from "effect";
import * as RpcMessage from "effect/unstable/rpc/RpcMessage";
import * as RpcSerialization from "effect/unstable/rpc/RpcSerialization";
import * as RpcServer from "effect/unstable/rpc/RpcServer";
import * as Socket from "effect/unstable/socket/Socket";

export const makeSocketRpcProtocol = Effect.gen(function* () {
  const serialization = yield* RpcSerialization.RpcSerialization;
  const disconnects = yield* Queue.make<number>();

  let nextClientId = 0;
  const clients = new Map<number, {
    readonly write: (response: RpcMessage.FromServerEncoded) => Effect.Effect<void>;
  }>();
  const clientIds = new Set<number>();

  let writeRequest!: (
    clientId: number,
    message: RpcMessage.FromClientEncoded,
  ) => Effect.Effect<void>;

  const onSocket = function* (
    socket: Socket.Socket,
    headers?: ReadonlyArray<[string, string]>,
  ) {
    const scope = yield* Effect.scope;
    const parser = serialization.makeUnsafe();
    const clientId = nextClientId++;

    yield* Scope.addFinalizerExit(scope, () => {
      clients.delete(clientId);
      clientIds.delete(clientId);
      return Queue.offer(disconnects, clientId);
    });

    const writeRaw = yield* socket.writer;
    const write = (response: RpcMessage.FromServerEncoded) => {
      try {
        const encoded = parser.encode(response);
        if (encoded === undefined) return Effect.void;
        return Effect.orDie(writeRaw(encoded));
      } catch (cause) {
        return Effect.orDie(
          writeRaw(parser.encode(RpcMessage.ResponseDefectEncoded(cause))!),
        );
      }
    };

    clients.set(clientId, { write });
    clientIds.add(clientId);

    yield* socket.runRaw((data) => {
      try {
        const decoded = parser.decode(data) as ReadonlyArray<RpcMessage.FromClientEncoded>;
        return Effect.forEach(decoded, (message) => {
          if (message._tag === "Request" && headers !== undefined) {
            return writeRequest(clientId, {
              ...message,
              headers: headers.concat(message.headers),
            });
          }
          return writeRequest(clientId, message);
        }, { discard: true });
      } catch (cause) {
        return writeRaw(parser.encode(RpcMessage.ResponseDefectEncoded(cause))!);
      }
    }).pipe(
      Effect.catchReason("SocketError", "SocketCloseError", () => Effect.void),
      Effect.orDie,
    );
  };

  const protocol = yield* RpcServer.Protocol.make((writeRequest_) => {
    writeRequest = writeRequest_;
    return Effect.succeed({
      disconnects,
      send: (clientId, response) => {
        const client = clients.get(clientId);
        if (client === undefined) return Effect.void;
        return Effect.orDie(client.write(response));
      },
      end: () => Effect.void,
      clientIds: Effect.sync(() => clientIds),
      initialMessage: Effect.succeedNone,
      supportsAck: true,
      supportsTransferables: false,
      supportsSpanPropagation: true,
    });
  });

  return { onSocket, protocol } as const;
});
