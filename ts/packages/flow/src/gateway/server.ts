/**
 * API Gateway — HTTP + WebSocket server.
 *
 * Replaces the Python aiohttp gateway with Fastify.
 * Uses Effect RPC over WebSocket for streaming client requests.
 *
 * Python reference: trustgraph-flow/trustgraph/gateway/service.py
 */

import Fastify, { type FastifyReply } from "fastify";
import websocketPlugin from "@fastify/websocket";
import { Clock, Config, Effect, Exit, Random, Scope } from "effect";
import * as O from "effect/Option";
import * as RpcSerialization from "effect/unstable/rpc/RpcSerialization";
import * as EffectSocket from "effect/unstable/socket/Socket";
import { messagingLifecycleError, optionalStringConfig, registry, toTgError, type PubSubBackend } from "@trustgraph/base";
import { makeDispatcherManager } from "./dispatch/manager.js";
import { makeGatewayRpcServer } from "./rpc-server.js";

export interface GatewayConfig {
  port: number;
  metricsPort: number;
  secret?: string;
  natsUrl?: string;
  pubsub?: PubSubBackend;
}

export function createGateway(config: GatewayConfig) {
  const app = Fastify({ logger: true });
  const dispatcher = makeDispatcherManager(config);

  const sendDispatchResult = (reply: FastifyReply, result: unknown): unknown => {
    const err = (result as Record<string, unknown>)?.error as { type?: string; message?: string } | undefined;
    if (err !== undefined) {
      const statusCode = err.type === "not-found" ? 404 : 400;
      return reply.code(statusCode).send(result);
    }
    return result;
  };

  const sendDispatchError = (reply: FastifyReply, error: unknown): unknown =>
    reply.code(500).send({ error: toTgError(error) });

  return Effect.runPromise(
    Effect.gen(function* () {
      yield* Effect.tryPromise({
        try: () => app.register(websocketPlugin),
        catch: (cause) => messagingLifecycleError("gateway", "register-websocket", cause),
      });

      yield* Effect.tryPromise({
        try: () => dispatcher.start(),
        catch: (cause) => messagingLifecycleError("gateway", "dispatcher-start", cause),
      });

      const rpcScope = yield* Scope.make();
      const rpcServer = yield* makeGatewayRpcServer(dispatcher).pipe(
        Effect.provideService(RpcSerialization.RpcSerialization, RpcSerialization.ndjson),
        Scope.provide(rpcScope),
      );

      return { rpcScope, rpcServer };
    }),
  ).then(({ rpcScope, rpcServer }) => {
      // Authentication middleware
      app.addHook("onRequest", (request, reply) => {
        if (request.url === "/api/v1/metrics") return;
        if (request.url.startsWith("/api/v1/rpc")) return; // RPC socket auth via query param

        if (config.secret !== undefined && config.secret.length > 0) {
          const auth = request.headers.authorization;
          if (auth === undefined || auth !== `Bearer ${config.secret}`) {
            reply.code(401).send({ error: "Unauthorized" });
          }
        }
      });

      app.post<{
        Body: {
          scope?: string;
          service?: string;
          flow?: string;
          request?: Record<string, unknown>;
        };
      }>("/api/v1/workbench/dispatch", (request, reply) => {
        const body = request.body;
        const service = body.service;
        const payload = body.request;
        if (service === undefined || service.length === 0 || payload === undefined) {
          return reply.code(400).send({
            error: { type: "bad-request", message: "service and request are required" },
          });
        }

        return Effect.runPromise(
          Effect.tryPromise({
            try: () =>
              body.scope === "flow"
                ? dispatcher.dispatchFlowService(body.flow ?? "default", service, payload)
                : dispatcher.dispatchGlobalService(service, payload),
            catch: (cause) => messagingLifecycleError("gateway", "workbench-dispatch", cause),
          }).pipe(
            Effect.map((result) => sendDispatchResult(reply, result)),
            Effect.catch((error) => Effect.succeed(sendDispatchError(reply, error))),
          ),
        );
      });

      // REST endpoint: POST /api/v1/:kind  (global services)
      app.post<{ Params: { kind: string } }>("/api/v1/:kind", (request, reply) => {
        const { kind } = request.params;
        const body = request.body as Record<string, unknown>;

        return Effect.runPromise(
          Effect.tryPromise({
            try: () => dispatcher.dispatchGlobalService(kind, body),
            catch: (cause) => messagingLifecycleError("gateway", "global-dispatch", cause),
          }).pipe(
            Effect.map((result) => sendDispatchResult(reply, result)),
            Effect.catch((error) => Effect.succeed(sendDispatchError(reply, error))),
          ),
        );
      });

      // REST endpoint: POST /api/v1/flow/:flow/service/:kind  (flow-scoped services)
      app.post<{ Params: { flow: string; kind: string } }>(
        "/api/v1/flow/:flow/service/:kind",
        (request, reply) => {
          const { flow, kind } = request.params;
          const body = request.body as Record<string, unknown>;

          return Effect.runPromise(
            Effect.tryPromise({
              try: () => dispatcher.dispatchFlowService(flow, kind, body),
              catch: (cause) => messagingLifecycleError("gateway", "flow-dispatch", cause),
            }).pipe(
              Effect.map((result) => sendDispatchResult(reply, result)),
              Effect.catch((error) => Effect.succeed(sendDispatchError(reply, error))),
            ),
          );
        },
      );

      // REST endpoint: POST /api/v1/flow/:flow/load  (trigger document processing)
      app.post<{ Params: { flow: string } }>(
        "/api/v1/flow/:flow/load",
        (request, reply) => {
          const { flow } = request.params;
          const body = request.body as {
            documentId?: string;
            user?: string;
            collection?: string;
          };

          if (body.documentId === undefined || body.documentId.length === 0) {
            return reply.code(400).send({
              error: { type: "bad-request", message: "documentId is required" },
            });
          }

          return Effect.runPromise(
            Effect.gen(function* () {
              const user = body.user ?? "default";
              const collection = body.collection ?? "default";
              const documentId = body.documentId;
              const timestamp = yield* Clock.currentTimeMillis;
              const suffix = yield* Random.nextIntBetween(0, 36 ** 6, { halfOpen: true });

              // Publish Document message to the decode-input topic
              const topic = "tg.flow.document";
              const metadata = {
                id: `load-${timestamp}-${suffix.toString(36).padStart(6, "0")}`,
                root: documentId,
                user,
                collection,
              };

              yield* Effect.tryPromise({
                try: () => dispatcher.publishToTopic(topic, { metadata, documentId }),
                catch: (cause) => messagingLifecycleError("gateway", "publish-load", cause),
              });

              return { status: "processing", documentId, flow };
            }).pipe(
              Effect.catch((error) => Effect.succeed(sendDispatchError(reply, error))),
            ),
          );
        },
      );

      // Effect RPC WebSocket endpoint: /api/v1/rpc
      app.get("/api/v1/rpc", { websocket: true }, (socket, request) => {
        const url = new URL(request.url, `http://${request.headers.host}`);
        const token = url.searchParams.get("token");
        if (config.secret !== undefined && config.secret.length > 0 && token !== config.secret) {
          socket.close(4001, "Unauthorized");
          return;
        }

        const program = Effect.scoped(
          Effect.gen(function* () {
            const effectSocket = yield* EffectSocket.fromWebSocket(
              Effect.succeed(socket as unknown as globalThis.WebSocket),
              { closeCodeIsError: (code) => code !== 1000 },
            );
            yield* rpcServer.onSocket(effectSocket, headersFrom(request.headers));
          }),
        );

        void Effect.runPromise(program.pipe(Scope.provide(rpcScope))).catch((error) => {
          void Effect.runPromise(
            Effect.logError("[Gateway] RPC WebSocket error", { error: toTgError(error).message }).pipe(
              Effect.flatMap(() =>
                Effect.sync(() => {
                  if (socket.readyState === 1) {
                    socket.close(1011, "Internal server error");
                  }
                }),
              ),
            ),
          );
        });
      });

      // Metrics endpoint — returns Prometheus metrics from prom-client
      app.get("/api/v1/metrics", (_, reply) => {
        reply.header("content-type", registry.contentType);
        return registry.metrics();
      });

      return {
        start: () => app.listen({ port: config.port, host: "0.0.0.0" }),
        stop: () =>
          Effect.runPromise(
            Effect.gen(function* () {
              yield* Effect.tryPromise({
                try: () => app.close(),
                catch: (cause) => messagingLifecycleError("gateway", "app-close", cause),
              });
              yield* Scope.close(rpcScope, Exit.void);
              yield* Effect.tryPromise({
                try: () => dispatcher.stop(),
                catch: (cause) => messagingLifecycleError("gateway", "dispatcher-stop", cause),
              });
            }),
          ),
      };
  });
}

function headersFrom(headers: Record<string, string | string[] | number | undefined>): ReadonlyArray<[string, string]> {
  return Object.entries(headers).flatMap(([key, value]) => {
    if (typeof value === "string") return [[key, value] satisfies [string, string]];
    if (typeof value === "number") return [[key, String(value)] satisfies [string, string]];
    if (Array.isArray(value)) return value.map((item) => [key, item] satisfies [string, string]);
    return [];
  });
}

export function run(): Promise<void> {
  return Effect.runPromise(program);
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

export const program = Effect.scoped(
  Effect.gen(function* () {
    const config = yield* loadGatewayConfig();
    const gateway = yield* Effect.promise(() => createGateway(config)).pipe(Effect.orDie);
    yield* Effect.addFinalizer(() => Effect.promise(() => gateway.stop()).pipe(Effect.orDie));
    yield* Effect.promise(() => gateway.start()).pipe(
      Effect.orDie,
      Effect.withSpan("trustgraph.gateway.start", {
        attributes: {
          "trustgraph.gateway.port": config.port,
        },
      }),
    );
    yield* Effect.log(`[Gateway] Listening on port ${config.port}`);
    return yield* Effect.never;
  }),
);
