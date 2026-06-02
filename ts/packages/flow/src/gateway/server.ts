/**
 * API Gateway — HTTP + WebSocket server.
 *
 * Replaces the Python aiohttp gateway with Fastify.
 * Uses Effect RPC over WebSocket for streaming client requests.
 *
 * Python reference: trustgraph-flow/trustgraph/gateway/service.py
 */

import Fastify from "fastify";
import websocketPlugin from "@fastify/websocket";
import { Config, Effect, Exit, Scope } from "effect";
import * as O from "effect/Option";
import * as RpcSerialization from "effect/unstable/rpc/RpcSerialization";
import * as EffectSocket from "effect/unstable/socket/Socket";
import { optionalStringConfig, registry, toTgError } from "@trustgraph/base";
import { makeDispatcherManager } from "./dispatch/manager.js";
import { makeGatewayRpcServer } from "./rpc-server.js";

export interface GatewayConfig {
  port: number;
  metricsPort: number;
  secret?: string;
  natsUrl?: string;
}

export async function createGateway(config: GatewayConfig) {
  const app = Fastify({ logger: true });
  await app.register(websocketPlugin);

  const dispatcher = makeDispatcherManager(config);
  await dispatcher.start();
  const rpcScope = await Effect.runPromise(Scope.make());
  const rpcServer = await Effect.runPromise(
    makeGatewayRpcServer(dispatcher).pipe(
      Effect.provideService(RpcSerialization.RpcSerialization, RpcSerialization.ndjson),
      Scope.provide(rpcScope),
    ),
  );

  // Authentication middleware
  app.addHook("onRequest", async (request, reply) => {
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
  }>("/api/v1/workbench/dispatch", async (request, reply) => {
    const body = request.body;
    const service = body.service;
    const payload = body.request;
    if (service === undefined || service.length === 0 || payload === undefined) {
      return reply.code(400).send({
        error: { type: "bad-request", message: "service and request are required" },
      });
    }

    try {
      const result = body.scope === "flow"
        ? await dispatcher.dispatchFlowService(body.flow ?? "default", service, payload)
        : await dispatcher.dispatchGlobalService(service, payload);
      const err = (result as Record<string, unknown>)?.error as { type?: string; message?: string } | undefined;
      if (err !== undefined) {
        const statusCode = err.type === "not-found" ? 404 : 400;
        return reply.code(statusCode).send(result);
      }
      return result;
    } catch (err) {
      reply.code(500).send({ error: toTgError(err) });
    }
  });

  // REST endpoint: POST /api/v1/:kind  (global services)
  app.post<{ Params: { kind: string } }>("/api/v1/:kind", async (request, reply) => {
    const { kind } = request.params;
    const body = request.body as Record<string, unknown>;

    try {
      const result = await dispatcher.dispatchGlobalService(kind, body) as Record<string, unknown>;
      const err = result?.error as { type?: string; message?: string } | undefined;
      if (err !== undefined) {
        const statusCode = err.type === "not-found" ? 404 : 400;
        return reply.code(statusCode).send(result);
      }
      return result;
    } catch (err) {
      reply.code(500).send({ error: toTgError(err) });
    }
  });

  // REST endpoint: POST /api/v1/flow/:flow/service/:kind  (flow-scoped services)
  app.post<{ Params: { flow: string; kind: string } }>(
    "/api/v1/flow/:flow/service/:kind",
    async (request, reply) => {
      const { flow, kind } = request.params;
      const body = request.body as Record<string, unknown>;

      try {
        const result = await dispatcher.dispatchFlowService(flow, kind, body) as Record<string, unknown>;
        const err = result?.error as { type?: string; message?: string } | undefined;
        if (err !== undefined) {
          const statusCode = err.type === "not-found" ? 404 : 400;
          return reply.code(statusCode).send(result);
        }
        return result;
      } catch (err) {
        reply.code(500).send({ error: toTgError(err) });
      }
    },
  );

  // REST endpoint: POST /api/v1/flow/:flow/load  (trigger document processing)
  app.post<{ Params: { flow: string } }>(
    "/api/v1/flow/:flow/load",
    async (request, reply) => {
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

      try {
        const user = body.user ?? "default";
        const collection = body.collection ?? "default";
        const documentId = body.documentId;

        // Publish Document message to the decode-input topic
        const topic = "tg.flow.document";
        const metadata = {
          id: `load-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
          root: documentId,
          user,
          collection,
        };

        await dispatcher.publishToTopic(topic, { metadata, documentId });

        return { status: "processing", documentId, flow };
      } catch (err) {
        reply.code(500).send({
          error: toTgError(err),
        });
      }
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

    Effect.runPromise(program.pipe(Scope.provide(rpcScope))).catch((err) => {
      console.error("[Gateway] RPC WebSocket error:", err);
      if (socket.readyState === 1) {
        socket.close(1011, "Internal server error");
      }
    });
  });

  // Metrics endpoint — returns Prometheus metrics from prom-client
  app.get("/api/v1/metrics", async (_, reply) => {
    reply.header("content-type", registry.contentType);
    return registry.metrics();
  });

  return {
    start: () => app.listen({ port: config.port, host: "0.0.0.0" }),
    stop: async () => {
      await app.close();
      await Effect.runPromise(Scope.close(rpcScope, Exit.void));
      await dispatcher.stop();
    },
  };
}

function headersFrom(headers: Record<string, string | string[] | number | undefined>): ReadonlyArray<[string, string]> {
  return Object.entries(headers).flatMap(([key, value]) => {
    if (typeof value === "string") return [[key, value] satisfies [string, string]];
    if (typeof value === "number") return [[key, String(value)] satisfies [string, string]];
    if (Array.isArray(value)) return value.map((item) => [key, item] satisfies [string, string]);
    return [];
  });
}

export async function run(): Promise<void> {
  await Effect.runPromise(program);
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
