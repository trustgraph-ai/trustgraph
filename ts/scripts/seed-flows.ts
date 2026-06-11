/**
 * Seed flow-manager flow instances for demos.
 *
 * Usage: bun run seed:flows
 * Requires: gateway + flow-manager + config service running
 */

import { BunRuntime } from "@effect/platform-bun";
import * as BunHttpClient from "@effect/platform-bun/BunHttpClient";
import { Array as A, Config, Effect, Order, Schema as S } from "effect";
import { HttpClient, HttpClientRequest, HttpClientResponse } from "effect/unstable/http";

const DEFAULT_GATEWAY_URL = "http://localhost:8088";

class SeedFlowsError extends S.TaggedErrorClass<SeedFlowsError>()(
  "SeedFlowsError",
  {
    operation: S.String,
    message: S.String,
  },
) {}

const GatewayErrorBody = S.Struct({
  message: S.optionalKey(S.String),
});

const FlowListResponse = S.Struct({
  "flow-ids": S.optionalKey(S.Array(S.String)),
  error: S.optionalKey(GatewayErrorBody),
});

const GatewayResponse = S.Struct({
  version: S.optionalKey(S.Number),
  error: S.optionalKey(GatewayErrorBody),
});

const stringifyJson = (operation: string, value: unknown) =>
  S.encodeUnknownEffect(S.UnknownFromJsonString)(value).pipe(
    Effect.mapError((cause) =>
      SeedFlowsError.make({
        operation,
        message: String(cause),
      })
    ),
  );

const decodeJsonText = (operation: string, value: string) =>
  S.decodeUnknownEffect(S.UnknownFromJsonString)(value).pipe(
    Effect.mapError((cause) =>
      SeedFlowsError.make({
        operation,
        message: String(cause),
      })
    ),
  );

const decodeWith = <A, I, R>(operation: string, schema: S.Codec<A, I, R>) => (value: unknown) =>
  S.decodeUnknownEffect(schema)(value).pipe(
    Effect.mapError((cause) =>
      SeedFlowsError.make({
        operation,
        message: String(cause),
      })
    ),
  );

const FLOW_TOPICS = {
  // Document processing pipeline
  "decode-input": "tg.flow.document",
  "decode-output": "tg.flow.text-document",
  "decode-triples": "tg.flow.triples",
  "chunk-input": "tg.flow.text-document",
  "chunk-output": "tg.flow.chunk",
  "chunk-triples": "tg.flow.triples",
  "extract-input": "tg.flow.chunk",
  "extract-triples": "tg.flow.triples",
  "extract-entity-contexts": "tg.flow.entity-contexts",
  // Storage consumers
  "store-triples-input": "tg.flow.triples",
  "store-graph-embeddings-input": "tg.flow.entity-contexts",
  // LLM text completion
  "text-completion-request": "tg.flow.text-completion-request",
  "text-completion-response": "tg.flow.text-completion-response",
  // Prompt service
  "prompt-request": "tg.flow.prompt-request",
  "prompt-response": "tg.flow.prompt-response",
  // Graph RAG
  "graph-rag-request": "tg.flow.graph-rag-request",
  "graph-rag-response": "tg.flow.graph-rag-response",
  // Document RAG
  "document-rag-request": "tg.flow.document-rag-request",
  "document-rag-response": "tg.flow.document-rag-response",
  // Triples query
  "triples-request": "tg.flow.triples-request",
  "triples-response": "tg.flow.triples-response",
  // Agent
  "agent-request": "tg.flow.agent-request",
  "agent-response": "tg.flow.agent-response",
  // Embeddings
  "embeddings-request": "tg.flow.embeddings-request",
  "embeddings-response": "tg.flow.embeddings-response",
  // Graph embeddings query
  "graph-embeddings-request": "tg.flow.graph-embeddings-request",
  "graph-embeddings-response": "tg.flow.graph-embeddings-response",
  // Document embeddings query
  "document-embeddings-request": "tg.flow.document-embeddings-request",
  "document-embeddings-response": "tg.flow.document-embeddings-response",
  // Librarian RPC (for PDF decoder)
  "librarian-request": "tg.flow.librarian-request",
  "librarian-response": "tg.flow.librarian-response",
  // MCP tool invocation
  "mcp-tool-request": "tg.flow.mcp-tool-request",
  "mcp-tool-response": "tg.flow.mcp-tool-response",
} as const;

const SEEDED_FLOWS = [
  {
    id: "default",
    description: "Full-stack default pipeline for ingestion, RAG, and agent demos.",
  },
  {
    id: "beep-hole",
    description: "Workbench sandbox flow for ad hoc experiments.",
  },
  {
    id: "ai-graph-demo",
    description: "Graph RAG over the seeded AI industry knowledge graph.",
  },
  {
    id: "doc-rag-demo",
    description: "Document RAG over the seeded demo document chunks.",
  },
  {
    id: "agent-demo",
    description: "Agent flow wired to seeded knowledge and document tools.",
  },
] as const;

const postJson = Effect.fn("seed-flows.postJson")(function* (
  gatewayUrl: string,
  path: string,
  body: Record<string, unknown>,
) {
  const bodyText = yield* stringifyJson("encode-request", body);
  const request = HttpClientRequest.post(`${gatewayUrl}${path}`, { acceptJson: true }).pipe(
    HttpClientRequest.bodyText(bodyText, "application/json"),
  );
  const response = yield* HttpClient.execute(request).pipe(
    Effect.flatMap(HttpClientResponse.filterStatusOk),
    Effect.mapError((cause) =>
      SeedFlowsError.make({
        operation: "http-request",
        message: String(cause),
      })
    ),
  );
  const responseText = yield* response.text.pipe(
    Effect.mapError((cause) =>
      SeedFlowsError.make({
        operation: "read-response",
        message: String(cause),
      })
    ),
  );
  return yield* decodeJsonText("decode-response-json", responseText);
});

const failOnGatewayError = Effect.fn("seed-flows.failOnGatewayError")(function* (
  operation: string,
  data: { readonly error?: { readonly message?: string } },
) {
  if (data.error !== undefined) {
    return yield* SeedFlowsError.make({
      operation,
      message: data.error.message ?? "unknown gateway error",
    });
  }
});

const listFlows = Effect.fn("seed-flows.listFlows")(function* (gatewayUrl: string) {
  const response = yield* postJson(gatewayUrl, "/api/v1/flow", {
    operation: "list-flows",
  }).pipe(Effect.flatMap(decodeWith("decode-flow-list", FlowListResponse)));
  yield* failOnGatewayError("list-flows", response);
  return new Set(response["flow-ids"] ?? []);
});

const startMissingFlows = Effect.fn("seed-flows.startMissingFlows")(function* (
  gatewayUrl: string,
  existing: Set<string>,
) {
  for (const flow of SEEDED_FLOWS) {
    if (existing.has(flow.id)) {
      console.log(`  Flow ${flow.id}: already running`);
      continue;
    }

    const response = yield* postJson(gatewayUrl, "/api/v1/flow", {
      operation: "start-flow",
      "flow-id": flow.id,
      "blueprint-name": "default",
      description: flow.description,
      parameters: {
        user: "default",
        collection: "default",
      },
    }).pipe(Effect.flatMap(decodeWith("decode-start-flow", GatewayResponse)));
    yield* failOnGatewayError("start-flow", response);
    existing.add(flow.id);
    console.log(`  Flow ${flow.id}: started`);
  }
});

const ensureFlowConfig = Effect.fn("seed-flows.ensureFlowConfig")(function* (gatewayUrl: string) {
  const values = Object.fromEntries(
    SEEDED_FLOWS.map((flow) => [flow.id, { topics: FLOW_TOPICS }]),
  );

  const response = yield* postJson(gatewayUrl, "/api/v1/config", {
    operation: "put",
    keys: ["flows"],
    values,
  }).pipe(Effect.flatMap(decodeWith("decode-flow-config", GatewayResponse)));
  yield* failOnGatewayError("flow-config", response);
  console.log(`  Flow config topics pushed -> version ${response.version ?? "unknown"}`);
});

const main = Effect.fn("seed-flows.main")(function* () {
  const gatewayUrl = yield* Config.string("GATEWAY_URL").pipe(Config.withDefault(DEFAULT_GATEWAY_URL));

  console.log("Seeding TrustGraph flows...\n");

  const existing = yield* listFlows(gatewayUrl);
  yield* startMissingFlows(gatewayUrl, existing);

  console.log("\nAligning flow config topics...");
  yield* ensureFlowConfig(gatewayUrl);

  const finalFlows = A.sort(Array.from(yield* listFlows(gatewayUrl)), Order.String);
  console.log(`\nActive flows: ${finalFlows.join(", ")}`);
  console.log("\nFlow seeding complete.");
});

BunRuntime.runMain(main().pipe(Effect.provide(BunHttpClient.layer)));
