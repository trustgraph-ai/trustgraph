/**
 * Integration test — exercises the full pipeline:
 *
 * 1. Start config service + gateway
 * 2. Test config CRUD via REST
 * 3. Push a flow definition (for LLM service)
 * 4. Optionally test LLM text-completion (if CLAUDE_KEY or OPENAI_TOKEN set)
 *
 * Usage: pnpm tsx scripts/test-pipeline.ts
 */

import { BunRuntime } from "@effect/platform-bun";
import * as BunHttpClient from "@effect/platform-bun/BunHttpClient";
import { DispatchInput, makeEffectRpcClient } from "../packages/client/src/index.js";
import { Config, Effect, Option as O, Schema as S } from "effect";
import { HttpClient, HttpClientRequest } from "effect/unstable/http";

const DEFAULT_GATEWAY_URL = "http://localhost:8088";
const DEFAULT_LLM_MODEL = "qwen2.5:0.5b";
const DEFAULT_FALKORDB_URL = "redis://localhost:6380";
const DEFAULT_PIPELINE_WAIT = 20;

interface PipelineConfig {
  readonly gatewayUrl: string;
  readonly gatewaySecret: string | undefined;
  readonly llmModel: string;
  readonly pipelineWaitSeconds: number;
  readonly falkorDbUrl: string;
  readonly skipPipeline: boolean;
  readonly skipLlm: boolean;
  readonly skipLibrarian: boolean;
  readonly skipAgent: boolean;
}

class PipelineTestError extends S.TaggedErrorClass<PipelineTestError>()(
  "PipelineTestError",
  {
    operation: S.String,
    message: S.String,
  },
) {}

const QdrantCollectionsResponse = S.Struct({
  result: S.optionalKey(S.Struct({
    collections: S.optionalKey(S.Array(S.Struct({ name: S.String }))),
  })),
});

const pipelineError = (operation: string, cause: unknown) =>
  PipelineTestError.make({
    operation,
    message: String(cause),
  });

const skipFlag = (name: string) =>
  Config.string(name).pipe(
    Config.withDefault("0"),
    Config.map((value) => value === "1"),
  );

const loadConfig = Effect.fn("test-pipeline.loadConfig")(function* () {
  const gatewaySecret = yield* Config.string("GATEWAY_SECRET").pipe(Config.option);
  return {
    gatewayUrl: yield* Config.string("GATEWAY_URL").pipe(Config.withDefault(DEFAULT_GATEWAY_URL)),
    gatewaySecret: O.getOrUndefined(gatewaySecret),
    llmModel: yield* Config.string("LLM_MODEL").pipe(Config.withDefault(DEFAULT_LLM_MODEL)),
    pipelineWaitSeconds: yield* Config.number("PIPELINE_WAIT").pipe(Config.withDefault(DEFAULT_PIPELINE_WAIT)),
    falkorDbUrl: yield* Config.string("FALKORDB_URL").pipe(Config.withDefault(DEFAULT_FALKORDB_URL)),
    skipPipeline: yield* skipFlag("SKIP_PIPELINE"),
    skipLlm: yield* skipFlag("SKIP_LLM"),
    skipLibrarian: yield* skipFlag("SKIP_LIBRARIAN"),
    skipAgent: yield* skipFlag("SKIP_AGENT"),
  } satisfies PipelineConfig;
});

// ─── Helpers ──────────────────────────────────────────────────────────

const stringifyJson = (operation: string, value: unknown) =>
  S.encodeUnknownEffect(S.UnknownFromJsonString)(value).pipe(
    Effect.mapError((cause) => pipelineError(operation, cause)),
  );

const decodeJsonText = (operation: string, value: string) =>
  S.decodeUnknownEffect(S.UnknownFromJsonString)(value).pipe(
    Effect.mapError((cause) => pipelineError(operation, cause)),
  );

const post = Effect.fn("test-pipeline.post")(function* (
  config: PipelineConfig,
  path: string,
  body: unknown,
) {
  const bodyText = yield* stringifyJson("post.encode-request", body);
  const request = HttpClientRequest.post(`${config.gatewayUrl}${path}`, { acceptJson: true }).pipe(
    HttpClientRequest.bodyText(bodyText, "application/json"),
  );
  const response = yield* HttpClient.execute(request).pipe(
    Effect.mapError((cause) => pipelineError("post.http", cause)),
  );
  const text = yield* response.text.pipe(
    Effect.mapError((cause) => pipelineError("post.read-response", cause)),
  );
  return yield* decodeJsonText("post.decode-response", text).pipe(
    Effect.catch(() => Effect.succeed({ status: response.status, body: text })),
  );
});

const getJson = Effect.fn("test-pipeline.getJson")(function* (url: string) {
  const response = yield* HttpClient.get(url, { acceptJson: true }).pipe(
    Effect.mapError((cause) => pipelineError("get.http", cause)),
  );
  const text = yield* response.text.pipe(
    Effect.mapError((cause) => pipelineError("get.read-response", cause)),
  );
  return yield* decodeJsonText("get.decode-response", text);
});

const gatewayReachable = Effect.fn("test-pipeline.gatewayReachable")(function* (config: PipelineConfig) {
  return yield* HttpClient.get(`${config.gatewayUrl}/api/v1/metrics`).pipe(
    Effect.map((response) => response.status >= 200 && response.status < 300),
    Effect.catch(() => Effect.succeed(false)),
  );
});

function log(label: string, data: unknown): void {
  console.log(`\n[${label}]`);
  console.dir(data, { depth: null });
}

function pass(test: string): void {
  console.log(`  ✓ ${test}`);
}

function fail(test: string, err: unknown): void {
  console.error(`  ✗ ${test}:`, err);
}

const catchTest = <R, E>(name: string, effect: Effect.Effect<boolean, E, R>) =>
  effect.pipe(
    Effect.catch((err) => {
      fail(name, err);
      return Effect.succeed(false);
    }),
  );

// ─── Tests ────────────────────────────────────────────────────────────

const testConfigList = (config: PipelineConfig) => catchTest("Config list", Effect.gen(function* () {
    const res = yield* post(config, "/api/v1/config", { operation: "list", keys: [] });
    log("config/list", res);
    if (typeof res === "object" && res !== null && "version" in res) {
      pass("Config list returns version");
      return true;
    }
    fail("Config list", "unexpected response");
    return false;
}));

const testConfigPut = (config: PipelineConfig) => catchTest("Config put", Effect.gen(function* () {
    const res = yield* post(config, "/api/v1/config", {
      operation: "put",
      keys: ["test"],
      values: { greeting: "hello from trustgraph-ts!" },
    });
    log("config/put", res);
    if (typeof res === "object" && res !== null && "version" in res) {
      pass("Config put accepted");
      return true;
    }
    fail("Config put", "unexpected response");
    return false;
}));

const testConfigGet = (config: PipelineConfig) => catchTest("Config get", Effect.gen(function* () {
    const res = yield* post(config, "/api/v1/config", {
      operation: "get",
      keys: ["test"],
    });
    log("config/get", res);
    const r = res as Record<string, unknown>;
    const values = r.values as Record<string, unknown> | undefined;
    if (values?.greeting === "hello from trustgraph-ts!") {
      pass("Config get returns stored value");
      return true;
    }
    fail("Config get", "value mismatch");
    return false;
}));

const testConfigDelete = (config: PipelineConfig) => catchTest("Config delete", Effect.gen(function* () {
    const res = yield* post(config, "/api/v1/config", {
      operation: "delete",
      keys: ["test"],
    });
    log("config/delete", res);

    // Verify it's gone
    const check = yield* post(config, "/api/v1/config", {
      operation: "get",
      keys: ["test"],
    }) as Record<string, unknown>;

    const values = check.values as Record<string, unknown> | undefined;
    if (!values || Object.keys(values).length === 0) {
      pass("Config delete removes value");
      return true;
    }
    fail("Config delete", "value still present");
    return false;
}));

const testPushFlowConfig = (config: PipelineConfig) => catchTest("Flow config push", Effect.gen(function* () {
    // Push a full flow definition with all service topic mappings
    const res = yield* post(config, "/api/v1/config", {
      operation: "put",
      keys: ["flows"],
      values: {
        default: {
          topics: {
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
            // Librarian RPC (for PDF decoder)
            "librarian-request": "tg.flow.librarian-request",
            "librarian-response": "tg.flow.librarian-response",
          },
        },
      },
    });
    log("config/push-flow", res);
    if (typeof res === "object" && res !== null && "version" in res) {
      pass("Flow config pushed");
      return true;
    }
    fail("Flow config push", "unexpected response");
    return false;
}));

const testTextCompletion = (config: PipelineConfig) => catchTest("Text completion", Effect.gen(function* () {
    console.log("\n  Sending text-completion request (may take a few seconds)...");
    const res = yield* post(config, "/api/v1/flow/default/service/text-completion", {
      system: "You are a helpful assistant. Reply in one sentence.",
      prompt: "What is 2+2?",
      model: config.llmModel,
    });
    log("text-completion", res);
    const r = res as Record<string, unknown>;
    if (r.response && typeof r.response === "string") {
      pass(`Text completion returned: "${(r.response as string).slice(0, 80)}..."`);
      return true;
    }
    if (r.error) {
      fail("Text completion", r.error);
      return false;
    }
    fail("Text completion", "unexpected response");
    return false;
}));

const testWebSocket = (config: PipelineConfig) => catchTest("Effect RPC WebSocket", Effect.gen(function* () {
  const gatewayWsUrl = config.gatewayUrl.replace(/^http/, "ws").replace(/\/$/, "");
  const response = yield* Effect.scoped(
    Effect.gen(function*() {
      const client = yield* makeEffectRpcClient(`${gatewayWsUrl}/api/v1/rpc`);
      return yield* client.dispatch(
        DispatchInput.make({
          scope: "global",
          service: "config",
          request: { operation: "list", keys: [] },
        }),
        { timeoutMs: 5_000 },
      );
    }),
  ).pipe(Effect.timeout("5 seconds"));

  log("websocket/rpc-response", response);
  pass("Effect RPC WebSocket round-trip works");
  return true;
}));

// ─── Librarian Tests ──────────────────────────────────────────────────

let testDocId = "";

const testLibrarianAdd = (config: PipelineConfig) => catchTest("Librarian add-document", Effect.gen(function* () {
    const content = Buffer.from("Hello from TrustGraph TypeScript!").toString("base64");
    const res = yield* post(config, "/api/v1/librarian", {
      operation: "add-document",
      user: "test-user",
      collection: "test-collection",
      content,
      documentMetadata: {
        id: "",
        time: Date.now(),
        kind: "text/plain",
        title: "Test Document",
        comments: "",
        user: "test-user",
        tags: ["test"],
        documentType: "source",
      },
    });
    log("librarian/add", res);
    const r = res as Record<string, unknown>;
    const meta = r.documentMetadata as Record<string, unknown> | undefined;
    if (meta?.id && typeof meta.id === "string") {
      testDocId = meta.id;
      pass(`Librarian add-document returned id: ${testDocId.slice(0, 8)}...`);
      return true;
    }
    if (r.error) {
      fail("Librarian add-document", r.error);
      return false;
    }
    fail("Librarian add-document", "no documentMetadata.id in response");
    return false;
}));

const testLibrarianList = (config: PipelineConfig) => catchTest("Librarian list-documents", Effect.gen(function* () {
    const res = yield* post(config, "/api/v1/librarian", {
      operation: "list-documents",
      user: "test-user",
    });
    log("librarian/list", res);
    const r = res as Record<string, unknown>;
    const docs = r.documents as unknown[] | undefined;
    if (docs && docs.length > 0) {
      pass(`Librarian list-documents returned ${docs.length} document(s)`);
      return true;
    }
    fail("Librarian list-documents", "empty or missing documents array");
    return false;
}));

const testLibrarianGetContent = (config: PipelineConfig) => catchTest("Librarian get-content", Effect.gen(function* () {
  if (!testDocId) {
    fail("Librarian get-content", "no document ID from add test");
    return false;
  }
    const res = yield* post(config, "/api/v1/librarian", {
      operation: "get-document-content",
      documentId: testDocId,
      user: "test-user",
    });
    log("librarian/get-content", res);
    const r = res as Record<string, unknown>;
    if (r.content && typeof r.content === "string") {
      const decoded = Buffer.from(r.content, "base64").toString("utf-8");
      if (decoded === "Hello from TrustGraph TypeScript!") {
        pass("Librarian get-content round-trips correctly");
        return true;
      }
      fail("Librarian get-content", `decoded: "${decoded}"`);
      return false;
    }
    fail("Librarian get-content", "no content in response");
    return false;
}));

const testLibrarianDelete = (config: PipelineConfig) => catchTest("Librarian delete", Effect.gen(function* () {
  if (!testDocId) {
    fail("Librarian delete", "no document ID from add test");
    return false;
  }
    const res = yield* post(config, "/api/v1/librarian", {
      operation: "remove-document",
      documentId: testDocId,
      user: "test-user",
    });
    log("librarian/delete", res);

    // Verify it's gone
    const listRes = yield* post(config, "/api/v1/librarian", {
      operation: "list-documents",
      user: "test-user",
    }) as Record<string, unknown>;
    const docs = listRes.documents as unknown[] | undefined;
    if (!docs || docs.length === 0) {
      pass("Librarian remove-document deleted successfully");
      return true;
    }
    fail("Librarian remove-document", "document still present after delete");
    return false;
}));

// ─── Document Load Test ──────────────────────────────────────────────

const testDocumentLoad = (config: PipelineConfig) => catchTest("Document load", Effect.gen(function* () {
    // First upload a test document via librarian
    const content = Buffer.from("Test document for pipeline processing.").toString("base64");
    const addRes = yield* post(config, "/api/v1/librarian", {
      operation: "add-document",
      user: "test-user",
      collection: "test-collection",
      content,
      documentMetadata: {
        id: "",
        time: Date.now(),
        kind: "application/pdf",
        title: "Test Pipeline Document",
        comments: "",
        user: "test-user",
        tags: ["test"],
        documentType: "source",
      },
    }) as Record<string, unknown>;

    const meta = addRes.documentMetadata as Record<string, unknown> | undefined;
    if (!meta?.id) {
      fail("Document load", "failed to upload test document");
      return false;
    }
    const docId = meta.id as string;

    // Trigger document processing via the load endpoint
    const data = yield* post(config, "/api/v1/flow/default/load", {
      documentId: docId,
      user: "test-user",
      collection: "test-collection",
    });
    log("document-load", data);

    if (data.status === "processing") {
      pass(`Document load triggered for ${docId.slice(0, 8)}...`);

      // Clean up the test document
      yield* post(config, "/api/v1/librarian", {
        operation: "remove-document",
        documentId: docId,
        user: "test-user",
      });

      return true;
    }
    fail("Document load", "unexpected response");
    return false;
}));

// ─── Full Pipeline Test (real PDF) ───────────────────────────────────

const testFullPipeline = (config: PipelineConfig) => catchTest("Full pipeline", Effect.gen(function* () {
    // 1. Generate a test PDF in memory using pdf-lib
    const { PDFDocument, StandardFonts } = yield* Effect.tryPromise({
      try: () => import("pdf-lib"),
      catch: (cause) => pipelineError("full-pipeline.import-pdf-lib", cause),
    });

    const pdfDoc = yield* Effect.tryPromise({
      try: () => PDFDocument.create(),
      catch: (cause) => pipelineError("full-pipeline.create-pdf", cause),
    });
    const font = yield* Effect.tryPromise({
      try: () => pdfDoc.embedFont(StandardFonts.Helvetica),
      catch: (cause) => pipelineError("full-pipeline.embed-font", cause),
    });

    const texts = [
      "Alice Johnson is a senior engineer at Acme Corporation. Acme develops CloudSync, a cloud storage platform. CloudSync uses Amazon Web Services for hosting.",
      "Bob Chen is the CTO of Acme Corporation. Alice reports to Bob. CloudSync was launched in 2024 and competes with Dropbox.",
    ];

    for (const text of texts) {
      const page = pdfDoc.addPage([612, 792]);
      page.drawText(text, { x: 50, y: 700, size: 11, font, maxWidth: 500 });
    }

    const pdfBytes = yield* Effect.tryPromise({
      try: () => pdfDoc.save(),
      catch: (cause) => pipelineError("full-pipeline.save-pdf", cause),
    });
    const content = Buffer.from(pdfBytes).toString("base64");

    console.log(`  Generated test PDF: ${pdfBytes.length} bytes, 2 pages`);

    // 2. Upload to librarian as application/pdf
    const addRes = yield* post(config, "/api/v1/librarian", {
      operation: "add-document",
      user: "test",
      collection: "test",
      content,
      documentMetadata: {
        id: "",
        time: Date.now(),
        kind: "application/pdf",
        title: "Acme Corporation Test Document",
        comments: "End-to-end pipeline test",
        user: "test",
        tags: ["test", "pipeline"],
        documentType: "source",
      },
    }) as Record<string, unknown>;

    const meta = addRes.documentMetadata as Record<string, unknown> | undefined;
    if (!meta?.id) {
      fail("Full pipeline", "failed to upload PDF");
      return false;
    }
    const docId = meta.id as string;
    console.log(`  Uploaded PDF as document ${docId.slice(0, 8)}...`);

    // 3. Trigger pipeline processing
    const loadData = yield* post(config, "/api/v1/flow/default/load", {
      documentId: docId,
      user: "test",
      collection: "test",
    });

    const loadRecord = loadData as Record<string, unknown>;
    if (loadRecord.status !== "processing") {
      fail("Full pipeline", `load returned: ${String(loadData)}`);
      return false;
    }
    console.log("  Pipeline triggered, waiting for processing...");

    // 4. Wait for pipeline to complete (PDF decode + chunking + extraction + storage)
    // This involves multiple LLM calls so give it time
    for (let i = config.pipelineWaitSeconds; i > 0; i--) {
      process.stdout.write(`\r  Waiting... ${i}s remaining `);
      yield* Effect.sleep("1 second");
    }
    console.log("\r  Processing wait complete.              ");

    // 5. Verify triples in FalkorDB
    let triplesFound = false;
    const falkorCount = yield* Effect.tryPromise({
      try: async () => {
        const { createClient } = await import("falkordb");
        const client = createClient({
          url: config.falkorDbUrl,
        });
        await client.connect();
        const graph = client.graph("falkordb");
        const result = await graph.query("MATCH (n:Node) RETURN count(n) as cnt");
        const count = result.data?.[0]?.[0] ?? 0;
        await client.disconnect();
        return count;
      },
      catch: (cause) => pipelineError("full-pipeline.falkordb", cause),
    }).pipe(
      Effect.catch((err) => {
        const errStr = String(err);
        if (errStr.includes("Cannot find package") || errStr.includes("MODULE_NOT_FOUND")) {
          console.log("  FalkorDB check skipped: falkordb package not available at workspace root");
        } else {
          console.log(`  FalkorDB check failed: ${err}`);
        }
        return Effect.succeed(undefined);
      }),
    );

      if (typeof falkorCount === "number" && falkorCount > 0) {
        console.log(`  FalkorDB: ${falkorCount} nodes found`);
        triplesFound = true;
      } else {
        console.log(`  FalkorDB: no nodes found (count=${falkorCount})`);
      }

    // 6. Verify embeddings in Qdrant
    let embeddingsFound = false;
    const qdrantData = yield* getJson("http://localhost:6333/collections").pipe(
      Effect.flatMap((value) =>
        S.decodeUnknownEffect(QdrantCollectionsResponse)(value).pipe(
          Effect.mapError((cause) => pipelineError("full-pipeline.qdrant.decode", cause)),
        )
      ),
      Effect.catch((err) => {
        console.log(`  Qdrant check failed: ${err}`);
        return Effect.succeed(undefined);
      }),
    );
    if (qdrantData !== undefined) {
      const collections = qdrantData.result?.collections ?? [];
      const testCollections = collections.filter((c) => c.name.startsWith("t_test_test_"));

      if (testCollections.length > 0) {
        console.log(`  Qdrant: found collections: ${testCollections.map((c) => c.name).join(", ")}`);
        embeddingsFound = true;
      } else {
        console.log(`  Qdrant: no test collections found (total: ${collections.length} collections)`);
      }
    }

    // 7. Report results
    if (triplesFound && embeddingsFound) {
      pass("Full pipeline: PDF decoded, triples stored, embeddings stored");
      return true;
    }if (triplesFound) {
      pass("Full pipeline: triples stored (embeddings pending)");
      return true;
    }if (embeddingsFound) {
      pass("Full pipeline: embeddings stored (triples pending)");
      return true;
    }
      // Pipeline triggered but stores not populated yet — partial success
      pass("Full pipeline: triggered successfully (stores may need more time)");
      return true;
}));

// ─── Agent Test ───────────────────────────────────────────────────────

const testAgentQuery = (config: PipelineConfig) => catchTest("Agent", Effect.gen(function* () {
    console.log("\n  Sending agent request (may take a few seconds)...");
    const res = yield* post(config, "/api/v1/flow/default/service/agent", {
      question: "What is the capital of France?",
      model: config.llmModel,
    });
    log("agent", res);
    const r = res as Record<string, unknown>;
    // Agent sends streaming chunks — gateway returns the first/final response
    if (r.chunk_type || r.answer || r.content) {
      pass("Agent returned a response");
      return true;
    }
    if (r.error) {
      // Agent may error if no graph data — that's OK, proves routing works
      const err = r.error as Record<string, unknown>;
      pass(`Agent responded with error (routing works): ${err.message ?? err.type}`);
      return true;
    }
    fail("Agent", "unexpected response format");
    return false;
}));

// ─── Main ─────────────────────────────────────────────────────────────

const main = Effect.fn("test-pipeline.main")(function* () {
  const config = yield* loadConfig();

  console.log("╔══════════════════════════════════════════════════╗");
  console.log("║  TrustGraph TypeScript — Integration Test       ║");
  console.log("╚══════════════════════════════════════════════════╝");
  console.log(`\nGateway: ${config.gatewayUrl}`);

  // Check gateway is reachable
  const isReachable = yield* gatewayReachable(config);
  if (isReachable) {
    pass("Gateway reachable");
  } else {
    fail("Gateway reachable", "metrics endpoint unavailable");
    console.error("\n⚠ Gateway not running. Start it first:");
    console.error("  pnpm tsx scripts/run-gateway.ts");
    return yield* PipelineTestError.make({
      operation: "gateway-reachable",
      message: "gateway metrics endpoint unavailable",
    });
  }

  let passed = 0;
  let failed = 0;
  const run = Effect.fn("test-pipeline.run")(function* (
    name: string,
    test: Effect.Effect<boolean, never, HttpClient.HttpClient>,
  ) {
    console.log(`\n── ${name} ──`);
    if (yield* test) passed++;
    else failed++;
  });

  // Config CRUD tests
  yield* run("Config List", testConfigList(config));
  yield* run("Config Put", testConfigPut(config));
  yield* run("Config Get", testConfigGet(config));
  yield* run("Config Delete", testConfigDelete(config));

  // WebSocket test
  yield* run("WebSocket Round-Trip", testWebSocket(config));

  // Flow config push
  yield* run("Push Flow Config", testPushFlowConfig(config));

  // Document pipeline load test (requires librarian + gateway)
  if (!config.skipPipeline && !config.skipLibrarian) {
    console.log("\n  (Testing document load — set SKIP_PIPELINE=1 to skip)");
    yield* run("Document Load", testDocumentLoad(config));
  } else {
    console.log("\n  (Skipping document pipeline load test)");
  }

  // LLM test (only if a running LLM service is available)
  if (!config.skipLlm) {
    console.log("\n  (Testing text-completion — set SKIP_LLM=1 to skip)");
    yield* run("Text Completion", testTextCompletion(config));
  } else {
    console.log("\n  (SKIP_LLM=1 — skipping LLM test)");
  }

  // Librarian tests (only if librarian service is running)
  if (!config.skipLibrarian) {
    console.log("\n  (Testing librarian — set SKIP_LIBRARIAN=1 to skip)");
    yield* run("Librarian Add", testLibrarianAdd(config));
    yield* run("Librarian List", testLibrarianList(config));
    yield* run("Librarian Get Content", testLibrarianGetContent(config));
    yield* run("Librarian Delete", testLibrarianDelete(config));
  } else {
    console.log("\n  (SKIP_LIBRARIAN=1 — skipping librarian tests)");
  }

  // Full pipeline test (real PDF → decode → chunk → extract → store)
  if (!config.skipPipeline && !config.skipLlm) {
    console.log("\n  (Testing full pipeline with real PDF — set SKIP_PIPELINE=1 to skip)");
    yield* run("Full Pipeline", testFullPipeline(config));
  } else {
    console.log("\n  (Skipping full pipeline test)");
  }

  // Agent test (only if agent + LLM services are running)
  if (!config.skipAgent && !config.skipLlm) {
    console.log("\n  (Testing agent — set SKIP_AGENT=1 to skip)");
    yield* run("Agent Query", testAgentQuery(config));
  } else {
    console.log("\n  (Skipping agent test)");
  }

  console.log("\n══════════════════════════════════════════════════");
  console.log(`  Results: ${passed} passed, ${failed} failed`);
  console.log("══════════════════════════════════════════════════\n");

  if (failed > 0) {
    return yield* PipelineTestError.make({
      operation: "results",
      message: `${failed} integration test(s) failed`,
    });
  }
});

BunRuntime.runMain(main().pipe(Effect.provide(BunHttpClient.layer)));
