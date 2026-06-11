import { describe, expect, it } from "@effect/vitest";
import { Effect, Exit, Scope } from "effect";
import { HttpRouter, HttpServerResponse } from "effect/unstable/http";
import type { DispatcherManager } from "../gateway/dispatch/manager.js";
import type { GatewayRpcServer } from "../gateway/rpc-server.js";
import type { GatewayConfig } from "../gateway/server.js";
import { makeGatewayRoutes, } from "../gateway/server.js";

interface DispatchCall {
  readonly scope: "global" | "flow";
  readonly flow?: string;
  readonly kind: string;
  readonly request: Record<string, unknown>;
}

interface PublishCall {
  readonly topic: string;
  readonly message: unknown;
  readonly id?: string;
}

interface RouteCalls {
  readonly dispatches: Array<DispatchCall>;
  readonly publishes: Array<PublishCall>;
  rpcCalls: number;
}

const makeFakeDispatcher = (
  calls: RouteCalls,
  response: unknown = { ok: true },
): DispatcherManager =>
  ({
    start: Effect.void,
    stop: Effect.void,
    dispatchGlobalService: (kind, request) =>
      Effect.sync(() => {
        calls.dispatches.push({ scope: "global", kind, request });
        return response;
      }),
    dispatchGlobalServiceStreaming: () => Effect.void,
    dispatchFlowService: (flow, kind, request) =>
      Effect.sync(() => {
        calls.dispatches.push({ scope: "flow", flow, kind, request });
        return response;
      }),
    dispatchFlowServiceStreaming: () => Effect.void,
    publishToTopic: (topic, message, id) =>
      Effect.sync(() => {
        calls.publishes.push(id === undefined ? { topic, message } : { topic, message, id });
      }),
  }) as DispatcherManager;

const makeRequest = (
  path: string,
  body: unknown,
  headers: Record<string, string> = {},
) =>
  new Request(`http://localhost${path}`, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      ...headers,
    },
    body: typeof body === "string" ? body : JSON.stringify(body),
  });

const makeRouteHarness = (
  config: GatewayConfig = { port: 0, metricsPort: 0, secret: "secret" },
  dispatchResponse?: unknown,
) =>
  Effect.gen(function* () {
    const rpcScope = yield* Scope.make();
    yield* Effect.addFinalizer(() => Scope.close(rpcScope, Exit.void));

    const calls: RouteCalls = {
      dispatches: [],
      publishes: [],
      rpcCalls: 0,
    };
    const dispatcher = makeFakeDispatcher(calls, dispatchResponse);
    const rpcServer: GatewayRpcServer = {
      httpEffect: Effect.sync(() => {
        calls.rpcCalls += 1;
        return HttpServerResponse.text("rpc ok");
      }),
    };
    const { handler, dispose } = HttpRouter.toWebHandler(
      makeGatewayRoutes(config, dispatcher, rpcServer, rpcScope),
      { disableLogger: true },
    );
    yield* Effect.addFinalizer(() => Effect.promise(() => dispose()));

    return { calls, handler };
  });

describe("gateway HTTP routes", () => {
  it.effect(
    "rejects protected dispatch routes without bearer auth before dispatching",
    Effect.fnUntraced(function* () {
      const { calls, handler } = yield* makeRouteHarness();

      const response = yield* Effect.promise(() =>
        handler(makeRequest("/api/v1/config", { operation: "get" }))
      );

      expect(response.status).toBe(401);
      expect(calls.dispatches).toEqual([]);
    }),
  );

  it.effect(
    "returns bad request for malformed and non-object JSON bodies",
    Effect.fnUntraced(function* () {
      const { calls, handler } = yield* makeRouteHarness();
      const headers = { authorization: "Bearer secret" };

      const malformed = yield* Effect.promise(() =>
        handler(makeRequest("/api/v1/config", "{", headers))
      );
      const malformedBody = yield* Effect.promise(() => malformed.json()) as { error?: { message?: string } };

      const arrayBody = yield* Effect.promise(() =>
        handler(makeRequest("/api/v1/config", [], headers))
      );
      const arrayBodyJson = yield* Effect.promise(() => arrayBody.json()) as { error?: { message?: string } };

      expect(malformed.status).toBe(400);
      expect(malformedBody.error?.message).toBe("request body must be valid JSON");
      expect(arrayBody.status).toBe(400);
      expect(arrayBodyJson.error?.message).toBe("request body must be a JSON object");
      expect(calls.dispatches).toEqual([]);
    }),
  );

  it.effect(
    "dispatches global and flow POST routes with parsed request objects",
    Effect.fnUntraced(function* () {
      const { calls, handler } = yield* makeRouteHarness(undefined, { answer: 42 });
      const headers = { authorization: "Bearer secret" };

      const globalResponse = yield* Effect.promise(() =>
        handler(makeRequest("/api/v1/config", { operation: "get", key: "demo" }, headers))
      );
      const flowResponse = yield* Effect.promise(() =>
        handler(makeRequest("/api/v1/flow/demo/service/text-completion", { prompt: "hi" }, headers))
      );

      expect(globalResponse.status).toBe(200);
      expect(flowResponse.status).toBe(200);
      expect(calls.dispatches).toEqual([
        {
          scope: "global",
          kind: "config",
          request: { operation: "get", key: "demo" },
        },
        {
          scope: "flow",
          flow: "demo",
          kind: "text-completion",
          request: { prompt: "hi" },
        },
      ]);
    }),
  );

  it.effect(
    "publishes flow load requests with generated metadata",
    Effect.fnUntraced(function* () {
      const { calls, handler } = yield* makeRouteHarness();

      const response = yield* Effect.promise(() =>
        handler(
          makeRequest(
            "/api/v1/flow/demo/load",
            { documentId: "doc-1", user: "alice", collection: "docs" },
            { authorization: "Bearer secret" },
          ),
        )
      );
      const body = yield* Effect.promise(() => response.json()) as { status?: string; documentId?: string; flow?: string };

      expect(response.status).toBe(200);
      expect(body).toEqual({ status: "processing", documentId: "doc-1", flow: "demo" });
      expect(calls.publishes).toHaveLength(1);
      expect(calls.publishes[0]?.topic).toBe("tg.flow.document");
      expect(calls.publishes[0]?.message).toMatchObject({
        documentId: "doc-1",
        metadata: {
          root: "doc-1",
          user: "alice",
          collection: "docs",
        },
      });
    }),
  );

  it.effect(
    "checks the RPC route token before delegating to the native websocket effect",
    Effect.fnUntraced(function* () {
      const { calls, handler } = yield* makeRouteHarness();

      const rejected = yield* Effect.promise(() =>
        handler(new Request("http://localhost/api/v1/rpc?token=wrong"))
      );
      const accepted = yield* Effect.promise(() =>
        handler(new Request("http://localhost/api/v1/rpc?token=secret"))
      );

      expect(rejected.status).toBe(401);
      expect(accepted.status).toBe(200);
      expect(yield* Effect.promise(() => accepted.text())).toBe("rpc ok");
      expect(calls.rpcCalls).toBe(1);
    }),
  );
});
