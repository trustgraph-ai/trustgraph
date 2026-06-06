import { Cause, Effect, Layer, Queue, Scope } from "effect";
import { HttpServerRequest, HttpServerResponse } from "effect/unstable/http";
import * as RpcSerialization from "effect/unstable/rpc/RpcSerialization";
import * as RpcServer from "effect/unstable/rpc/RpcServer";
import { errorMessage } from "@trustgraph/base";
import type { DispatcherManager, DispatcherStreamError } from "./dispatch/manager.js";
import { DispatchError, DispatchPayload, DispatchStreamChunk, TrustGraphRpcs } from "./rpc-contract.js";

export interface GatewayRpcServer {
  readonly httpEffect: Effect.Effect<
    HttpServerResponse.HttpServerResponse,
    never,
    Scope.Scope | HttpServerRequest.HttpServerRequest
  >;
}

export const makeGatewayRpcServer = Effect.fn("makeGatewayRpcServer")(function* (
  dispatcher: DispatcherManager,
) {
  const { httpEffect, protocol } = yield* RpcServer.makeProtocolWithHttpEffectWebsocket;

  const serverLayer = RpcServer.layer(TrustGraphRpcs, {
    disableFatalDefects: true,
  }).pipe(
    Layer.provide(Layer.succeed(RpcServer.Protocol, protocol)),
    Layer.provide(makeGatewayRpcHandlers(dispatcher)),
    Layer.provide(RpcSerialization.layerNdjson),
  );

  yield* Layer.launch(serverLayer).pipe(Effect.forkScoped);

  return {
    httpEffect,
  } satisfies GatewayRpcServer;
});

const makeGatewayRpcHandlers = (dispatcher: DispatcherManager) =>
  TrustGraphRpcs.toLayer(Effect.succeed(
    TrustGraphRpcs.of({
      Dispatch: (payload) =>
        dispatchOne(dispatcher, payload).pipe(
          Effect.mapError((cause) => DispatchError.make({ message: errorMessage(cause) })),
        ),
      DispatchStream: Effect.fn("GatewayRpc.DispatchStream")(function* (payload) {
        const queue = yield* Queue.bounded<DispatchStreamChunk, DispatchError | Cause.Done>(16);
        yield* Effect.addFinalizer(() => Queue.shutdown(queue));

        yield* dispatchStreamEffect(dispatcher, payload, (response, complete) =>
          Queue.offer(queue, DispatchStreamChunk.make({ response, complete })),
        ).pipe(
          Effect.flatMap(() => Queue.end(queue)),
          Effect.catch((cause) => Queue.fail(queue, DispatchError.make({ message: errorMessage(cause) }))),
          Effect.forkScoped,
        );

        return queue;
      }),
    }),
  ));

function dispatchOne(
  dispatcher: DispatcherManager,
  payload: DispatchPayload,
): Effect.Effect<unknown, DispatcherStreamError> {
  if (payload.scope === "flow") {
    return dispatcher.dispatchFlowService(
      payload.flow ?? "default",
      payload.service,
      payload.request,
    );
  }
  return dispatcher.dispatchGlobalService(payload.service, payload.request);
}

function dispatchStreamEffect(
  dispatcher: DispatcherManager,
  payload: DispatchPayload,
  responder: (response: unknown, complete: boolean) => Effect.Effect<void>,
): Effect.Effect<void, DispatcherStreamError> {
  if (payload.scope === "flow") {
    return dispatcher.dispatchFlowServiceStreaming(
      payload.flow ?? "default",
      payload.service,
      payload.request,
      responder,
    );
  }

  return dispatcher.dispatchGlobalServiceStreaming(
    payload.service,
    payload.request,
    responder,
  );
}
