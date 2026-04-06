/**
 * API Gateway — HTTP + WebSocket server.
 *
 * Replaces the Python aiohttp gateway with Fastify.
 *
 * Python reference: trustgraph-flow/trustgraph/gateway/service.py
 */

import Fastify from "fastify";
import websocketPlugin from "@fastify/websocket";
import { DispatcherManager } from "./dispatch/manager.js";

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
    if (request.url === "/api/v1/socket") return; // Socket auth via query param

    if (config.secret) {
      const auth = request.headers.authorization;
      if (!auth || auth !== `Bearer ${config.secret}`) {
        reply.code(401).send({ error: "Unauthorized" });
      }
    }
  });

  // REST endpoint: POST /api/v1/:kind
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

  // REST endpoint: POST /api/v1/flow/:flow/service/:kind
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

  // WebSocket endpoint: /api/v1/socket
  app.get("/api/v1/socket", { websocket: true }, (socket, request) => {
    // Auth via query param
    const url = new URL(request.url, `http://${request.headers.host}`);
    const token = url.searchParams.get("token");
    if (config.secret && token !== config.secret) {
      socket.close(4001, "Unauthorized");
      return;
    }

    socket.on("message", async (data) => {
      try {
        const msg = JSON.parse(data.toString());
        const { id, service, flow, request: req } = msg;

        const responder = async (response: unknown, complete: boolean) => {
          socket.send(JSON.stringify({ id, response, complete }));
        };

        if (flow) {
          await dispatcher.dispatchFlowServiceStreaming(flow, service, req, responder);
        } else {
          await dispatcher.dispatchGlobalServiceStreaming(service, req, responder);
        }
      } catch (err) {
        const msg = JSON.parse(data.toString());
        socket.send(
          JSON.stringify({
            id: msg.id,
            error: { type: "internal", message: String(err) },
            complete: true,
          }),
        );
      }
    });

    socket.on("close", () => {
      // Cleanup
    });
  });

  // Metrics endpoint
  app.get("/api/v1/metrics", async () => {
    const { registry } = await import("@trustgraph/base");
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
