import { Cause, Effect, Layer, Queue, Scope } from "effect";
import * as RpcSerialization from "effect/unstable/rpc/RpcSerialization";
import * as RpcServer from "effect/unstable/rpc/RpcServer";
import type * as Socket from "effect/unstable/socket/Socket";
import { errorMessage } from "@trustgraph/base";
import type { DispatcherManager } from "./dispatch/manager.js";
import { DispatchError, DispatchPayload, DispatchStreamChunk, TrustGraphRpcs } from "./rpc-contract.js";
import { makeSocketRpcProtocol } from "./rpc-protocol.js";

export interface GatewayRpcServer {
  readonly onSocket: (
    socket: Socket.Socket,
    headers?: ReadonlyArray<[string, string]>,
  ) => Effect.Effect<void, never, Scope.Scope>;
}

export const makeGatewayRpcServer = Effect.fn("makeGatewayRpcServer")(function* (
  dispatcher: DispatcherManager,
) {
  const { onSocket, protocol } = yield* makeSocketRpcProtocol;

  const serverLayer = RpcServer.layer(TrustGraphRpcs, {
    disableFatalDefects: true,
  }).pipe(
    Layer.provide(Layer.succeed(RpcServer.Protocol, protocol)),
    Layer.provide(makeGatewayRpcHandlers(dispatcher)),
    Layer.provide(RpcSerialization.layerNdjson),
  );

  yield* Layer.launch(serverLayer).pipe(Effect.forkScoped);

  return {
    onSocket: Effect.fn("GatewayRpc.onSocket")(function* (socket, headers) {
      yield* onSocket(socket, headers);
    }),
  } satisfies GatewayRpcServer;
});

const makeGatewayRpcHandlers = (dispatcher: DispatcherManager) =>
  TrustGraphRpcs.toLayer(Effect.succeed(
    TrustGraphRpcs.of({
      Dispatch: (payload) =>
        Effect.tryPromise({
          try: () => dispatchOne(dispatcher, payload),
          catch: (cause) => new DispatchError({ message: errorMessage(cause) }),
        }),
      DispatchStream: Effect.fn("GatewayRpc.DispatchStream")(function* (payload) {
        const context = yield* Effect.context<never>();
        const runPromise = Effect.runPromiseWith(context);
        const queue = yield* Queue.bounded<DispatchStreamChunk, DispatchError | Cause.Done>(16);
        yield* Effect.addFinalizer(() => Queue.shutdown(queue));

        yield* Effect.tryPromise({
          try: () =>
            dispatchStream(dispatcher, payload, async (response, complete) => {
              await runPromise(Queue.offer(queue, new DispatchStreamChunk({ response, complete })));
              return complete;
            }),
          catch: (cause) => new DispatchError({ message: errorMessage(cause) }),
        }).pipe(
          Effect.flatMap(() => Queue.end(queue)),
          Effect.catch((error) => Queue.fail(queue, error)),
          Effect.forkScoped,
        );

        return queue;
      }),
    }),
  ));

function dispatchOne(
  dispatcher: DispatcherManager,
  payload: DispatchPayload,
): Promise<unknown> {
  if (payload.scope === "flow") {
    return dispatcher.dispatchFlowService(
      payload.flow ?? "default",
      payload.service,
      payload.request,
    );
  }
  return dispatcher.dispatchGlobalService(payload.service, payload.request);
}

async function dispatchStream(
  dispatcher: DispatcherManager,
  payload: DispatchPayload,
  responder: (response: unknown, complete: boolean) => Promise<boolean>,
): Promise<void> {
  const send = async (response: unknown, complete: boolean) => {
    await responder(response, complete);
  };

  if (payload.scope === "flow") {
    await dispatcher.dispatchFlowServiceStreaming(
      payload.flow ?? "default",
      payload.service,
      payload.request,
      send,
    );
    return;
  }

  await dispatcher.dispatchGlobalServiceStreaming(
    payload.service,
    payload.request,
    send,
  );
}
