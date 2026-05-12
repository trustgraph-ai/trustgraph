/**
 * API Gateway — HTTP + WebSocket server.
 *
 * Replaces the Python aiohttp gateway with Fastify.
 * Uses the Mux class for WebSocket multiplexing (queue-based request
 * buffering, concurrency control, proper task lifecycle).
 *
 * Python reference: trustgraph-flow/trustgraph/gateway/service.py
 */

import Fastify from "fastify";
import websocketPlugin from "@fastify/websocket";
import { Config, Effect } from "effect";
import * as O from "effect/Option";
import { errorMessage, optionalStringConfig, registry, toTgError } from "@trustgraph/base";
import { DispatcherManager } from "./dispatch/manager.js";
import { Mux, type MuxRequest, type MuxHandler } from "./dispatch/mux.js";

export interface GatewayConfig {
  port: number;
  metricsPort: number;
  secret?: string;
  natsUrl?: string;
}

export async function createGateway(config: GatewayConfig) {
  const app = Fastify({ logger: true });
  await app.register(websocketPlugin);

  const dispatcher = new DispatcherManager(config);
  await dispatcher.start();

  // Authentication middleware
  app.addHook("onRequest", async (request, reply) => {
    if (request.url === "/api/v1/metrics") return;
    if (request.url.startsWith("/api/v1/socket")) return; // Socket auth via query param

    if (config.secret !== undefined && config.secret.length > 0) {
      const auth = request.headers.authorization;
      if (auth === undefined || auth !== `Bearer ${config.secret}`) {
        reply.code(401).send({ error: "Unauthorized" });
      }
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

  // WebSocket endpoint: /api/v1/socket
  // Uses Mux for queue-based request buffering and concurrency control.
  app.get("/api/v1/socket", { websocket: true }, (socket, request) => {
    // Auth via query param
    const url = new URL(request.url, `http://${request.headers.host}`);
    const token = url.searchParams.get("token");
    if (config.secret !== undefined && config.secret.length > 0 && token !== config.secret) {
      socket.close(4001, "Unauthorized");
      return;
    }

    // Build the MuxHandler that dispatches to the DispatcherManager
    const handler: MuxHandler = async (muxReq, respond) => {
      if (muxReq.flow !== undefined && muxReq.flow.length > 0) {
        await dispatcher.dispatchFlowServiceStreaming(
          muxReq.flow,
          muxReq.service,
          muxReq.request,
          respond,
        );
      } else {
        await dispatcher.dispatchGlobalServiceStreaming(
          muxReq.service,
          muxReq.request,
          respond,
        );
      }
    };

    const mux = new Mux(handler);

    // Start the Mux run loop — sends responses back over the socket
    const runPromise = mux.run((data) => {
      // Only send if the socket is still open (readyState 1 = OPEN)
      if (socket.readyState === 1) {
        socket.send(data);
      }
    });

    // Incoming messages get queued into the Mux
    socket.on("message", (data) => {
      try {
        const msg = JSON.parse(data.toString()) as {
          id?: string;
          service?: string;
          flow?: string;
          request?: Record<string, unknown>;
        };

        if (
          msg.id === undefined ||
          msg.id.length === 0 ||
          msg.service === undefined ||
          msg.service.length === 0 ||
          msg.request === undefined
        ) {
          socket.send(
            JSON.stringify({
              id: msg.id ?? null,
              error: { type: "bad-request", message: "Missing id, service, or request" },
              complete: true,
            }),
          );
          return;
        }

        const muxReq: MuxRequest = {
          id: msg.id,
          service: msg.service,
          request: msg.request,
          ...(msg.flow !== undefined ? { flow: msg.flow } : {}),
        };

        mux.receive(muxReq);
      } catch (err) {
        socket.send(
          JSON.stringify({
            error: { type: "parse-error", message: errorMessage(err) },
            complete: true,
          }),
        );
      }
    });

    socket.on("close", () => {
      mux.stop();
    });

    socket.on("error", () => {
      mux.stop();
    });

    // Ensure runPromise errors don't go unhandled
    runPromise.catch((err) => {
      console.error("[Gateway] Mux run loop error:", err);
      mux.stop();
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
      await dispatcher.stop();
    },
  };
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
