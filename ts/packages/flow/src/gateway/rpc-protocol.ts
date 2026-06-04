import { Effect, Queue, Scope } from "effect";
import * as MutableHashMap from "effect/MutableHashMap";
import * as MutableHashSet from "effect/MutableHashSet";
import * as O from "effect/Option";
import * as S from "effect/Schema";
import * as RpcMessage from "effect/unstable/rpc/RpcMessage";
import * as RpcSerialization from "effect/unstable/rpc/RpcSerialization";
import * as RpcServer from "effect/unstable/rpc/RpcServer";
import * as Socket from "effect/unstable/socket/Socket";

export class RpcProtocolDecodeError extends S.TaggedErrorClass<RpcProtocolDecodeError>()(
  "RpcProtocolDecodeError",
  {
    message: S.String,
    cause: S.Unknown,
  },
) {}

const HeaderSchema = S.mutable(S.Tuple([S.String, S.String]));
const FromClientEncodedSchema = S.Union([
  S.TaggedStruct("Request", {
    id: S.String,
    tag: S.String,
    payload: S.Unknown,
    headers: S.Array(HeaderSchema),
    traceId: S.optionalKey(S.String),
    spanId: S.optionalKey(S.String),
    sampled: S.optionalKey(S.Boolean),
  }),
  S.TaggedStruct("Ack", {
    requestId: S.String,
  }),
  S.TaggedStruct("Interrupt", {
    requestId: S.String,
  }),
  S.TaggedStruct("Ping", {}),
  S.TaggedStruct("Eof", {}),
]).pipe(S.toTaggedUnion("_tag"));
const FromClientEncodedMessagesSchema = S.Array(FromClientEncodedSchema);
const decodeFromClientMessages = S.decodeUnknownEffect(FromClientEncodedMessagesSchema);

export const makeSocketRpcProtocol = Effect.gen(function* () {
  const serialization = yield* RpcSerialization.RpcSerialization;
  const disconnects = yield* Queue.make<number>();

  let nextClientId = 0;
  const clients = MutableHashMap.empty<number, {
    readonly write: (response: RpcMessage.FromServerEncoded) => Effect.Effect<void>;
  }>();
  const clientIds = MutableHashSet.empty<number>();

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
      MutableHashMap.remove(clients, clientId);
      MutableHashSet.remove(clientIds, clientId);
      return Queue.offer(disconnects, clientId);
    });

    const writeRaw = yield* socket.writer;
    const writeDefect = (cause: unknown) =>
      Effect.sync(() => parser.encode(RpcMessage.ResponseDefectEncoded(cause))).pipe(
        Effect.flatMap((encoded) => encoded === undefined ? Effect.void : writeRaw(encoded)),
      );
    const write = (response: RpcMessage.FromServerEncoded) =>
      Effect.sync(() => parser.encode(response)).pipe(
        Effect.flatMap((encoded) =>
          encoded === undefined ? Effect.void : Effect.orDie(writeRaw(encoded)),
        ),
        Effect.catchDefect((cause: unknown) =>
          writeDefect(cause).pipe(Effect.orDie),
        ),
      );

    MutableHashMap.set(clients, clientId, { write });
    MutableHashSet.add(clientIds, clientId);

    yield* socket.runRaw((data) =>
      Effect.try({
        try: () => parser.decode(data),
        catch: (cause) =>
          RpcProtocolDecodeError.make({
            message: "Failed to decode RPC socket frame",
            cause,
          }),
      }).pipe(
        Effect.flatMap((raw) =>
          decodeFromClientMessages(raw).pipe(
            Effect.mapError((cause) =>
              RpcProtocolDecodeError.make({
                message: "RPC socket frame did not contain valid client messages",
                cause,
              })
            ),
          )
        ),
        Effect.flatMap((decoded) =>
          Effect.forEach(decoded, (message) => {
            if (message._tag === "Request" && headers !== undefined) {
              return writeRequest(clientId, {
                ...message,
                headers: headers.concat(message.headers),
              });
            }
            return writeRequest(clientId, message);
          }, { discard: true }),
        ),
        Effect.catch((cause) => writeDefect(cause)),
        Effect.catchDefect((cause: unknown) => writeDefect(cause)),
      )
    ).pipe(
      Effect.catchReason("SocketError", "SocketCloseError", () => Effect.void),
      Effect.orDie,
    );
  };

  const protocol = yield* RpcServer.Protocol.make((writeRequest_) => {
    writeRequest = writeRequest_;
    return Effect.succeed({
      disconnects,
      send: (clientId, response) =>
        O.match(MutableHashMap.get(clients, clientId), {
          onNone: () => Effect.void,
          onSome: (client) => Effect.orDie(client.write(response)),
        }),
      end: () => Effect.void,
      clientIds: Effect.sync(() => new Set(clientIds)),
      initialMessage: Effect.succeedNone,
      supportsAck: true,
      supportsTransferables: false,
      supportsSpanPropagation: true,
    });
  });

  return { onSocket, protocol } as const;
});
