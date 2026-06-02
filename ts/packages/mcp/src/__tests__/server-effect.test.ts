import { describe, expect, it } from "vitest";
import {
  makeTrustGraphMcpStdioLayer,
  runStdio,
  TrustGraphMcpToolkit,
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

describe("Effect MCP server", () => {
  it("keeps the canonical Effect toolkit names stable", () => {
    expect(Object.keys(TrustGraphMcpToolkit.tools)).toEqual(expectedToolNames);
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
