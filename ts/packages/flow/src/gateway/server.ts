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
import * as RpcSerialization from "effect/unstable/rpc/RpcSerialization";
import {
  formatPrometheusMetrics,
  messagingLifecycleError,
  optionalStringConfig,
  prometheusContentType,
  toTgError,
  type PubSubBackend,
} from "@trustgraph/base";
import { makeDispatcherManager, type DispatcherManager } from "./dispatch/manager.js";
import { makeGatewayRpcServer, type GatewayRpcServer } from "./rpc-server.js";

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
  const body = yield* request.json;
  return isRecord(body) ? body : {};
});

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
    Effect.gen(function* () {
      const body = yield* readJsonRecord.pipe(
        Effect.catch(() => Effect.succeed<Record<string, unknown>>({})),
      );
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
    }),
  );

const globalDispatch = (
  config: GatewayConfig,
  dispatcher: DispatcherManager,
) =>
  withBearerAuth(
    config,
    Effect.gen(function* () {
      const params = yield* HttpRouter.params;
      const body = yield* readJsonRecord.pipe(
        Effect.catch(() => Effect.succeed<Record<string, unknown>>({})),
      );
      return yield* withDispatchError(
        dispatcher.dispatchGlobalService(params.kind ?? "", body),
        "global-dispatch",
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
      const body = yield* readJsonRecord.pipe(
        Effect.catch(() => Effect.succeed<Record<string, unknown>>({})),
      );
      return yield* withDispatchError(
        dispatcher.dispatchFlowService(params.flow ?? "default", params.kind ?? "", body),
        "flow-dispatch",
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
      const body = yield* readJsonRecord.pipe(
        Effect.catch(() => Effect.succeed<Record<string, unknown>>({})),
      );
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
    ),
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

    const socket = yield* request.upgrade;
    yield* rpcServer.onSocket(socket, headersFrom(request.headers)).pipe(
      Scope.provide(rpcScope),
    );
    return HttpServerResponse.empty();
  }).pipe(
    Effect.catch((error) => Effect.succeed(dispatchError(error))),
  );

const metricsRoute =
  formatPrometheusMetrics.pipe(
    Effect.map((body) =>
      HttpServerResponse.text(body, {
        headers: { "content-type": prometheusContentType },
      })
    ),
  );

const gatewayRoutes = (
  config: GatewayConfig,
  dispatcher: DispatcherManager,
  rpcServer: GatewayRpcServer,
  rpcScope: Scope.Scope,
) =>
  Layer.mergeAll(
    HttpRouter.add("POST", "/api/v1/workbench/dispatch", workbenchDispatch(config, dispatcher)),
    HttpRouter.add("POST", "/api/v1/:kind", globalDispatch(config, dispatcher)),
    HttpRouter.add("POST", "/api/v1/flow/:flow/service/:kind", flowDispatch(config, dispatcher)),
    HttpRouter.add("POST", "/api/v1/flow/:flow/load", flowLoad(config, dispatcher)),
    HttpRouter.add("GET", "/api/v1/rpc", rpcRoute(config, rpcServer, rpcScope)),
    HttpRouter.add("GET", "/api/v1/metrics", metricsRoute),
  );

export function createGateway(config: GatewayConfig) {
  return Layer.effectDiscard(
    Effect.scoped(Effect.gen(function* () {
      const dispatcher = makeDispatcherManager(config);
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
        gatewayRoutes(config, dispatcher, rpcServer, rpcScope),
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

function headersFrom(headers: Record<string, string | string[] | number | undefined>): ReadonlyArray<[string, string]> {
  return Object.entries(headers).flatMap(([key, value]) => {
    if (typeof value === "string") return [[key, value] satisfies [string, string]];
    if (typeof value === "number") return [[key, String(value)] satisfies [string, string]];
    if (Array.isArray(value)) return value.map((item) => [key, item] satisfies [string, string]);
    return [];
  });
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
