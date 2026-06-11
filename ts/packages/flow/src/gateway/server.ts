/** @effect-diagnostics nodeBuiltinImport:skip-file effectFnOpportunity:skip-file catchToOrElseSucceed:skip-file */
/**
 * API Gateway -- Effect HTTP + RPC server.
 *
 * Python reference: trustgraph-flow/trustgraph/gateway/service.py
 */

import { createServer } from "node:http";
import { NodeHttpServer, NodeRuntime } from "@effect/platform-node";
import { Clock, Config, Effect, Exit, Layer, Random, Scope } from "effect";
import * as O from "effect/Option";
import { HttpRouter, HttpServerRequest, HttpServerResponse } from "effect/unstable/http";
import { HttpApiBuilder } from "effect/unstable/httpapi";
import * as RpcSerialization from "effect/unstable/rpc/RpcSerialization";
import type {
  PubSubBackend,
} from "@trustgraph/base";
import {
  formatPrometheusMetrics,
  messagingLifecycleError,
  optionalStringConfig,
  prometheusContentType,
  toTgError,
} from "@trustgraph/base";
import { GatewayWorkbenchHttpApi } from "@trustgraph/client/rpc/contract";
import type { DispatcherManager } from "./dispatch/manager.js";
import { makeDispatcherManagerScoped, } from "./dispatch/manager.js";
import type { GatewayRpcServer } from "./rpc-server.js";
import { makeGatewayRpcServer, } from "./rpc-server.js";

export interface GatewayConfig {
  port: number;
  metricsPort: number;
  secret?: string;
  natsUrl?: string;
  pubsub?: PubSubBackend;
}

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

const json = (body: unknown, status = 200) =>
  HttpServerResponse.jsonUnsafe(body, { status });

const badRequest = (message: string) =>
  json({ error: { type: "bad-request", message } }, 400);

const dispatchError = (error: unknown) =>
  json({ error: toTgError(error) }, 500);

const dispatchResult = (result: unknown) => {
  const err = isRecord(result) && isRecord(result.error)
    ? result.error as { readonly type?: string; readonly message?: string }
    : undefined;
  if (err !== undefined) {
    return json(result, err.type === "not-found" ? 404 : 400);
  }
  return json(result);
};

const readJsonRecord = Effect.gen(function* () {
  const request = yield* HttpServerRequest.HttpServerRequest;
  const body = yield* request.json.pipe(
    Effect.mapError(() => "request body must be valid JSON"),
  );
  if (!isRecord(body)) {
    return yield* Effect.fail("request body must be a JSON object");
  }
  return body;
});

const withJsonRecord = <R>(
  use: (body: Record<string, unknown>) => Effect.Effect<HttpServerResponse.HttpServerResponse, never, R>,
): Effect.Effect<HttpServerResponse.HttpServerResponse, never, HttpServerRequest.HttpServerRequest | R> =>
  readJsonRecord.pipe(
    Effect.matchEffect({
      onFailure: (message) => Effect.succeed(badRequest(message)),
      onSuccess: use,
    }),
  );

const bearerAuthResponse = (config: GatewayConfig) =>
  Effect.gen(function* () {
    if (config.secret === undefined || config.secret.length === 0) return null;
    const request = yield* HttpServerRequest.HttpServerRequest;
    const auth = request.headers.authorization;
    return auth === `Bearer ${config.secret}`
      ? null
      : json({ error: "Unauthorized" }, 401);
  });

type RouteRequirements =
  | HttpServerRequest.HttpServerRequest
  | HttpRouter.RouteContext;

const withBearerAuth = (
  config: GatewayConfig,
  handler: Effect.Effect<HttpServerResponse.HttpServerResponse, never, RouteRequirements>,
) =>
  Effect.gen(function* () {
    const denied = yield* bearerAuthResponse(config);
    if (denied !== null) return denied;
    return yield* handler;
  });

const withDispatchError = <A, E>(
  effect: Effect.Effect<A, E>,
  operation: string,
): Effect.Effect<HttpServerResponse.HttpServerResponse> =>
  effect.pipe(
    Effect.mapError((cause) => messagingLifecycleError("gateway", operation, cause)),
    Effect.map(dispatchResult),
    Effect.catch((error) => Effect.succeed(dispatchError(error))),
  );

const workbenchDispatch = (
  config: GatewayConfig,
  dispatcher: DispatcherManager,
) =>
  withBearerAuth(
    config,
    withJsonRecord((body) =>
      Effect.gen(function* () {
        const service = typeof body.service === "string" ? body.service : undefined;
        const payload = isRecord(body.request) ? body.request : undefined;
        if (service === undefined || service.length === 0 || payload === undefined) {
          return badRequest("service and request are required");
        }

        const dispatch = body.scope === "flow"
          ? dispatcher.dispatchFlowService(
              typeof body.flow === "string" ? body.flow : "default",
              service,
              payload,
            )
          : dispatcher.dispatchGlobalService(service, payload);

        return yield* withDispatchError(dispatch, "workbench-dispatch");
      })
    ),
  );

const gatewayWorkbenchHttpApiRoutes = (
  config: GatewayConfig,
  dispatcher: DispatcherManager,
) => {
  const handlers = HttpApiBuilder.group(
    GatewayWorkbenchHttpApi,
    "workbench",
    (handlers) =>
      handlers.handleRaw("dispatch", () => workbenchDispatch(config, dispatcher)),
  );

  return HttpApiBuilder.layer(GatewayWorkbenchHttpApi).pipe(
    Layer.provide(handlers),
  );
};

const globalDispatch = (
  config: GatewayConfig,
  dispatcher: DispatcherManager,
) =>
  withBearerAuth(
    config,
    Effect.gen(function* () {
      const params = yield* HttpRouter.params;
      return yield* withJsonRecord((body) =>
        withDispatchError(
          dispatcher.dispatchGlobalService(params.kind ?? "", body),
          "global-dispatch",
        )
      );
    }),
  );

const flowDispatch = (
  config: GatewayConfig,
  dispatcher: DispatcherManager,
) =>
  withBearerAuth(
    config,
    Effect.gen(function* () {
      const params = yield* HttpRouter.params;
      return yield* withJsonRecord((body) =>
        withDispatchError(
          dispatcher.dispatchFlowService(params.flow ?? "default", params.kind ?? "", body),
          "flow-dispatch",
        )
      );
    }),
  );

const flowLoad = (
  config: GatewayConfig,
  dispatcher: DispatcherManager,
) =>
  withBearerAuth(
    config,
    Effect.gen(function* () {
      const params = yield* HttpRouter.params;
      return yield* withJsonRecord((body) =>
        Effect.gen(function* () {
          const documentId = typeof body.documentId === "string" ? body.documentId : undefined;
          if (documentId === undefined || documentId.length === 0) {
            return badRequest("documentId is required");
          }

          const user = typeof body.user === "string" ? body.user : "default";
          const collection = typeof body.collection === "string" ? body.collection : "default";
          const timestamp = yield* Clock.currentTimeMillis;
          const suffix = yield* Random.nextIntBetween(0, 36 ** 6, { halfOpen: true });
          const metadata = {
            id: `load-${timestamp}-${suffix.toString(36).padStart(6, "0")}`,
            root: documentId,
            user,
            collection,
          };

          yield* dispatcher.publishToTopic("tg.flow.document", { metadata, documentId }).pipe(
            Effect.mapError((cause) => messagingLifecycleError("gateway", "publish-load", cause)),
          );

          return json({ status: "processing", documentId, flow: params.flow ?? "default" });
        }).pipe(
          Effect.catch((error) => Effect.succeed(dispatchError(error))),
        )
      );
    }),
  );

const rpcRoute = (
  config: GatewayConfig,
  rpcServer: GatewayRpcServer,
  rpcScope: Scope.Scope,
) =>
  Effect.gen(function* () {
    const request = yield* HttpServerRequest.HttpServerRequest;
    const url = new URL(request.url, "http://localhost");
    const token = url.searchParams.get("token");
    if (config.secret !== undefined && config.secret.length > 0 && token !== config.secret) {
      return json({ error: "Unauthorized" }, 401);
    }

    return yield* rpcServer.httpEffect.pipe(
      Scope.provide(rpcScope),
    );
  });

const metricsRoute =
  formatPrometheusMetrics.pipe(
    Effect.map((body) =>
      HttpServerResponse.text(body, {
        headers: { "content-type": prometheusContentType },
      })
    ),
  );

export const makeGatewayRoutes = (
  config: GatewayConfig,
  dispatcher: DispatcherManager,
  rpcServer: GatewayRpcServer,
  rpcScope: Scope.Scope,
) =>
  Layer.mergeAll(
    gatewayWorkbenchHttpApiRoutes(config, dispatcher),
    HttpRouter.add("POST", "/api/v1/:kind", globalDispatch(config, dispatcher)),
    HttpRouter.add("POST", "/api/v1/flow/:flow/service/:kind", flowDispatch(config, dispatcher)),
    HttpRouter.add("POST", "/api/v1/flow/:flow/load", flowLoad(config, dispatcher)),
    HttpRouter.add("GET", "/api/v1/rpc", rpcRoute(config, rpcServer, rpcScope)),
    HttpRouter.add("GET", "/api/v1/metrics", metricsRoute),
  );

export function createGateway(config: GatewayConfig) {
  return Layer.effectDiscard(
    Effect.scoped(Effect.gen(function* () {
      const dispatcher = yield* makeDispatcherManagerScoped(config);
      yield* dispatcher.start.pipe(
        Effect.mapError((cause) => messagingLifecycleError("gateway", "dispatcher-start", cause)),
      );
      yield* Effect.addFinalizer(() =>
        dispatcher.stop.pipe(
          Effect.catch((cause) =>
            Effect.logError("[Gateway] Failed to stop dispatcher", {
              error: cause.message,
              operation: cause.operation,
            }),
          ),
        ),
      );

      const rpcScope = yield* Scope.make();
      yield* Effect.addFinalizer(() => Scope.close(rpcScope, Exit.void));
      const rpcServer = yield* makeGatewayRpcServer(dispatcher).pipe(
        Effect.provideService(RpcSerialization.RpcSerialization, RpcSerialization.ndjson),
        Scope.provide(rpcScope),
      );

      const serverLayer = HttpRouter.serve(
        makeGatewayRoutes(config, dispatcher, rpcServer, rpcScope),
      ).pipe(
        Layer.provideMerge(NodeHttpServer.layer(createServer, {
          port: config.port,
          host: "0.0.0.0",
        })),
      );

      yield* Effect.log(`[Gateway] Listening on port ${config.port}`);
      return yield* Layer.launch(serverLayer);
    })),
  );
}

export function runMain(): void {
  NodeRuntime.runMain(program);
}

export const loadGatewayConfig = Effect.fn("loadGatewayConfig")(function* () {
  const secret = O.getOrUndefined(yield* Config.string("GATEWAY_SECRET").pipe(Config.option));
  const natsUrl = yield* optionalStringConfig("NATS_URL");
  const port = yield* Config.number("GATEWAY_PORT").pipe(Config.withDefault(8088));
  const metricsPort = yield* Config.number("METRICS_PORT").pipe(Config.withDefault(8000));
  return {
    port,
    metricsPort,
    ...(secret !== undefined ? { secret } : {}),
    ...(natsUrl !== undefined ? { natsUrl } : {}),
  } satisfies GatewayConfig;
});

export const gatewayProgram = (config: GatewayConfig) => Layer.launch(createGateway(config));

export const program = loadGatewayConfig().pipe(
  Effect.flatMap(gatewayProgram),
);
