import { describe, expect, it, vi } from "vitest";
import * as Predicate from "effect/Predicate";
import { createMcpServer } from "../server.js";
import {
  makeTrustGraphMcpStdioLayer,
  runStdio,
  TrustGraphMcpToolkit,
} from "../server-effect.js";

const clientMock = vi.hoisted(() => ({
  createTrustGraphSocket: vi.fn(() => ({
    close: vi.fn(),
  })),
}));

vi.mock("@trustgraph/client", () => ({
  createTrustGraphSocket: clientMock.createTrustGraphSocket,
}));

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

const registeredToolNames = (value: unknown): Array<string> => {
  if (!Predicate.isObject(value) || !Predicate.hasProperty(value, "_registeredTools")) {
    return [];
  }
  return Predicate.isObject(value._registeredTools)
    ? Object.keys(value._registeredTools)
    : [];
};

describe("Effect MCP server", () => {
  it("keeps the canonical Effect toolkit names stable", () => {
    expect(Object.keys(TrustGraphMcpToolkit.tools)).toEqual(expectedToolNames);
  });

  it("keeps legacy SDK stdio tools aligned with the Effect toolkit", () => {
    const { server, socket } = createMcpServer({
      gatewayUrl: "ws://localhost:8088/api/v1/rpc",
      user: "mcp-test",
      flowId: "default",
    });

    expect(registeredToolNames(server)).toEqual(Object.keys(TrustGraphMcpToolkit.tools));
    expect(socket.close).toEqual(expect.any(Function));
  });

  it("exposes an Effect stdio layer and process entrypoint", () => {
    expect(
      makeTrustGraphMcpStdioLayer({
        gatewayUrl: "ws://localhost:8088/api/v1/rpc",
        user: "mcp-test",
        flowId: "default",
        openAiApiKey: "test-key",
      }),
    ).toBeDefined();

    expect(runStdio).toEqual(expect.any(Function));
  });
});
