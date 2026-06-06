import { describe, expect, it } from "@effect/vitest";
import type { BaseApi } from "@trustgraph/client";
import { Effect, Layer, Stream } from "effect";
import * as S from "effect/Schema";
import { LanguageModel, McpServer } from "effect/unstable/ai";
import * as McpSchema from "effect/unstable/ai/McpSchema";
import { FetchHttpClient, HttpRouter } from "effect/unstable/http";
import { RpcSerialization } from "effect/unstable/rpc";
import * as RpcClient from "effect/unstable/rpc/RpcClient";
import {
  makeTrustGraphMcpStdioLayer,
  runStdio,
  TrustGraphMcpConfig,
  TrustGraphMcpToolkit,
  TrustGraphMcpToolkitLive,
  TrustGraphSocket,
} from "../server-effect.js";

const expectedToolNames = [
  "text_completion",
  "graph_rag",
  "document_rag",
  "agent",
  "embeddings",
  "triples_query",
  "graph_embeddings_query",
  "get_config_all",
  "get_config",
  "put_config",
  "delete_config",
  "get_flows",
  "get_flow",
  "start_flow",
  "stop_flow",
  "get_documents",
  "load_document",
  "remove_document",
  "get_prompts",
  "get_prompt",
  "get_knowledge_cores",
  "delete_kg_core",
  "load_kg_core",
];

interface FakeSocketCalls {
  readonly flowIds: Array<string>;
  readonly graphRag: Array<{
    readonly query: string;
    readonly options: unknown;
    readonly collection: string | undefined;
  }>;
}

interface NativeTestClientOptions {
  readonly languageText?: string | undefined;
  readonly graphRag?: (() => Promise<string>) | undefined;
}

const decodeJsonText = S.decodeUnknownSync(S.UnknownFromJsonString);

const makeFakeSocket = (
  options: {
    readonly graphRag?: (() => Promise<string>) | undefined;
  } = {},
) => {
  const calls: FakeSocketCalls = {
    flowIds: [],
    graphRag: [],
  };

  const socket = {
    close: () => {},
    flow: (flowId: string) => {
      calls.flowIds.push(flowId);
      return {
        textCompletion: () => Promise.resolve("legacy text completion should not be used"),
        graphRag: (query: string, ragOptions: unknown, collection?: string) => {
          calls.graphRag.push({ query, options: ragOptions, collection });
          return options.graphRag === undefined
            ? Promise.resolve("graph rag answer")
            : options.graphRag();
        },
        documentRag: () => Promise.resolve("document rag answer"),
        agent: (
          _question: string,
          _onThought: () => void,
          _onObservation: () => void,
          onAnswer: (chunk: string, complete: boolean) => void,
        ) => onAnswer("agent answer", true),
        embeddings: () => Promise.resolve([[0.25, 0.75]]),
        triplesQuery: () => Promise.resolve([]),
        graphEmbeddingsQuery: () => Promise.resolve([]),
      };
    },
    config: () => ({
      getConfigAll: () => Promise.resolve({}),
      getConfig: () => Promise.resolve({}),
      putConfig: () => Promise.resolve({ ok: true }),
      deleteConfig: () => Promise.resolve({ ok: true }),
      getPrompts: () => Promise.resolve([]),
      getPrompt: () => Promise.resolve({}),
    }),
    flows: () => ({
      getFlows: () => Promise.resolve(["default"]),
      getFlow: () => Promise.resolve({}),
      startFlow: () => Promise.resolve({ ok: true }),
      stopFlow: () => Promise.resolve({ ok: true }),
    }),
    librarian: () => ({
      getDocuments: () => Promise.resolve([]),
      loadDocument: () => Promise.resolve({ ok: true }),
      removeDocument: () => Promise.resolve({ ok: true }),
    }),
    knowledge: () => ({
      getKnowledgeCores: () => Promise.resolve([]),
      deleteKgCore: () => Promise.resolve({ ok: true }),
      loadKgCore: () => Promise.resolve({ ok: true }),
    }),
  } as unknown as BaseApi;

  return { socket, calls };
};

const makeLanguageModelLayer = (text: string) =>
  Layer.effect(
    LanguageModel.LanguageModel,
    LanguageModel.make({
      generateText: () => Effect.succeed([{ type: "text", text }]),
      streamText: () => Stream.empty,
    }),
  );

const testConfig = TrustGraphMcpConfig.of({
  gatewayUrl: "ws://localhost:8088/api/v1/rpc",
  user: "mcp-test",
  token: undefined,
  flowId: "default",
  name: "trustgraph",
  version: "0.1.0-test",
  mcpPath: "/mcp",
  openAiModel: "test-model",
  openAiApiKey: undefined,
  port: 3000,
});

const makeNativeTestClient = (
  options: NativeTestClientOptions = {},
) =>
  makeNativeTestClientEffect(options);

const makeNativeTestClientEffect = Effect.fn("makeNativeTestClient")(function*(
  options: NativeTestClientOptions,
) {
  const { socket, calls } = makeFakeSocket({ graphRag: options.graphRag });
  const serverLayer = McpServer.toolkit(TrustGraphMcpToolkit).pipe(
    Layer.provide(TrustGraphMcpToolkitLive),
    Layer.provide(makeLanguageModelLayer(options.languageText ?? "direct ai answer")),
    Layer.provide(Layer.succeed(TrustGraphSocket, TrustGraphSocket.of(socket))),
    Layer.provide(Layer.succeed(TrustGraphMcpConfig, testConfig)),
    Layer.provide(McpServer.layerHttp({
      name: "trustgraph",
      version: "0.1.0-test",
      path: "/mcp",
    })),
  );

  const { handler, dispose } = HttpRouter.toWebHandler(serverLayer, { disableLogger: true });
  yield* Effect.addFinalizer(() => Effect.promise(() => dispose()));

  let sessionId: string | null = null;
  const customFetch = Object.assign(
    (input: RequestInfo | URL, init?: RequestInit) => {
      const request = input instanceof Request ? input : new Request(input, init);
      if (sessionId !== null) {
        request.headers.set("Mcp-Session-Id", sessionId);
      }
      return handler(request).then((response) => {
        sessionId = response.headers.get("Mcp-Session-Id");
        return response;
      });
    },
    { preconnect: fetch.preconnect },
  ) as typeof fetch;

  const clientLayer = RpcClient.layerProtocolHttp({ url: "http://localhost/mcp" }).pipe(
    Layer.provideMerge([FetchHttpClient.layer, RpcSerialization.layerJsonRpc()]),
    Layer.provide(Layer.succeed(FetchHttpClient.Fetch, customFetch)),
  );
  const client = yield* RpcClient.make(McpSchema.ClientRpcs).pipe(
    // @effect-diagnostics-next-line strictEffectProvide:off
    Effect.provide(clientLayer),
  );

  yield* client.initialize({
    protocolVersion: "9999-01-01",
    capabilities: {},
    clientInfo: {
      name: "trustgraph-mcp-test-client",
      version: "0.1.0-test",
    },
  });

  return { client, calls };
  });

const textContent = (result: McpSchema.CallToolResult): string => {
  const [content] = result.content;
  expect(content?.type).toBe("text");
  return "text" in content! ? content.text : "";
};

describe("Effect MCP server", () => {
  it.effect(
    "keeps the canonical Effect toolkit names stable",
    Effect.fnUntraced(function*() {
      expect(Object.keys(TrustGraphMcpToolkit.tools)).toEqual(expectedToolNames);
    }),
  );

  it.effect(
    "exposes an Effect stdio layer and process entrypoint",
    Effect.fnUntraced(function*() {
      expect(
        makeTrustGraphMcpStdioLayer({
          gatewayUrl: "ws://localhost:8088/api/v1/rpc",
          user: "mcp-test",
          flowId: "default",
          openAiApiKey: "test-key",
        }),
      ).toBeDefined();

      expect(runStdio).toEqual(expect.any(Function));
    }),
  );

  it.effect(
    "lists native MCP tools through the protocol bridge",
    Effect.fnUntraced(function*() {
      yield* Effect.scoped(Effect.gen(function*() {
        const { client } = yield* makeNativeTestClient();

        const result = yield* client["tools/list"]({});
        expect(result.tools.map((tool) => tool.name)).toEqual(expectedToolNames);
        expect(result.tools.find((tool) => tool.name === "graph_rag")?.annotations).toMatchObject({
          title: "Graph RAG",
          readOnlyHint: true,
          destructiveHint: false,
          openWorldHint: true,
        });
      }));
    }),
  );

  it.effect(
    "calls text_completion through the direct Effect language model",
    Effect.fnUntraced(function*() {
      yield* Effect.scoped(Effect.gen(function*() {
        const { client, calls } = yield* makeNativeTestClient({
          languageText: "direct model response",
        });

        const result = yield* client["tools/call"]({
          name: "text_completion",
          arguments: {
            system: "You are concise.",
            prompt: "Say hello.",
          },
        });

        expect(result.isError).toBe(false);
        expect(result.structuredContent).toEqual({ text: "direct model response" });
        expect(decodeJsonText(textContent(result))).toEqual({ text: "direct model response" });
        expect(calls.flowIds).toEqual([]);
      }));
    }),
  );

  it.effect(
    "calls gateway-backed tools through the native MCP bridge",
    Effect.fnUntraced(function*() {
      yield* Effect.scoped(Effect.gen(function*() {
        const { client, calls } = yield* makeNativeTestClient();

        const result = yield* client["tools/call"]({
          name: "graph_rag",
          arguments: {
            query: "Who knows Alice?",
            entity_limit: 4,
            triple_limit: 8,
            collection: "qa",
          },
        });

        expect(result.isError).toBe(false);
        expect(result.structuredContent).toEqual({ text: "graph rag answer" });
        expect(calls.graphRag).toEqual([
          {
            query: "Who knows Alice?",
            options: { entityLimit: 4, tripleLimit: 8 },
            collection: "qa",
          },
        ]);
      }));
    }),
  );

  it.effect(
    "returns JSON-safe structured failures for expected tool errors",
    Effect.fnUntraced(function*() {
      yield* Effect.scoped(Effect.gen(function*() {
        const { client } = yield* makeNativeTestClient({
          graphRag: () => Promise.reject(new Error("gateway unavailable")),
        });

        const result = yield* client["tools/call"]({
          name: "graph_rag",
          arguments: {
            query: "Will this fail?",
          },
        });

        expect(result.structuredContent).toEqual({
          _tag: "GraphRagError",
          message: "gateway unavailable",
        });
        expect(result.structuredContent).not.toHaveProperty("cause");
        expect(decodeJsonText(textContent(result))).toEqual(result.structuredContent);
      }));
    }),
  );
});
