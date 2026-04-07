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
import { registry } from "@trustgraph/base";
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

    if (config.secret) {
      const auth = request.headers.authorization;
      if (!auth || auth !== `Bearer ${config.secret}`) {
        reply.code(401).send({ error: "Unauthorized" });
      }
    }
  });

  // REST endpoint: POST /api/v1/:kind  (global services)
  app.post<{ Params: { kind: string } }>("/api/v1/:kind", async (request, reply) => {
    const { kind } = request.params;
    const body = request.body as Record<string, unknown>;

    try {
      const result = await dispatcher.dispatchGlobalService(kind, body);
      return result;
    } catch (err) {
      reply.code(500).send({ error: { type: "internal", message: String(err) } });
    }
  });

  // REST endpoint: POST /api/v1/flow/:flow/service/:kind  (flow-scoped services)
  app.post<{ Params: { flow: string; kind: string } }>(
    "/api/v1/flow/:flow/service/:kind",
    async (request, reply) => {
      const { flow, kind } = request.params;
      const body = request.body as Record<string, unknown>;

      try {
        const result = await dispatcher.dispatchFlowService(flow, kind, body);
        return result;
      } catch (err) {
        reply.code(500).send({ error: { type: "internal", message: String(err) } });
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

      if (!body.documentId) {
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
          error: { type: "internal", message: String(err) },
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
    if (config.secret && token !== config.secret) {
      socket.close(4001, "Unauthorized");
      return;
    }

    // Build the MuxHandler that dispatches to the DispatcherManager
    const handler: MuxHandler = async (muxReq, respond) => {
      if (muxReq.flow) {
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

        if (!msg.id || !msg.service || !msg.request) {
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
          flow: msg.flow,
          request: msg.request,
        };

        mux.receive(muxReq);
      } catch (err) {
        socket.send(
          JSON.stringify({
            error: { type: "parse-error", message: String(err) },
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
  const config: GatewayConfig = {
    port: parseInt(process.env.GATEWAY_PORT ?? "8088", 10),
    metricsPort: parseInt(process.env.METRICS_PORT ?? "8000", 10),
    secret: process.env.GATEWAY_SECRET,
    natsUrl: process.env.NATS_URL,
  };

  const gateway = await createGateway(config);
  await gateway.start();
  console.log(`[Gateway] Listening on port ${config.port}`);
}
