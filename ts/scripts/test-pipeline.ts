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

const GATEWAY_URL = process.env.GATEWAY_URL ?? "http://localhost:8088";

// ─── Helpers ──────────────────────────────────────────────────────────

async function post(path: string, body: unknown): Promise<unknown> {
  const res = await fetch(`${GATEWAY_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const text = await res.text();
  try {
    return JSON.parse(text);
  } catch {
    return { status: res.status, body: text };
  }
}

function log(label: string, data: unknown): void {
  console.log(`\n[${label}]`, JSON.stringify(data, null, 2));
}

function pass(test: string): void {
  console.log(`  ✓ ${test}`);
}

function fail(test: string, err: unknown): void {
  console.error(`  ✗ ${test}:`, err);
}

// ─── Tests ────────────────────────────────────────────────────────────

async function testConfigList(): Promise<boolean> {
  try {
    const res = await post("/api/v1/config", { operation: "list", keys: [] });
    log("config/list", res);
    if (typeof res === "object" && res !== null && "version" in res) {
      pass("Config list returns version");
      return true;
    }
    fail("Config list", "unexpected response");
    return false;
  } catch (err) {
    fail("Config list", err);
    return false;
  }
}

async function testConfigPut(): Promise<boolean> {
  try {
    const res = await post("/api/v1/config", {
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
  } catch (err) {
    fail("Config put", err);
    return false;
  }
}

async function testConfigGet(): Promise<boolean> {
  try {
    const res = await post("/api/v1/config", {
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
  } catch (err) {
    fail("Config get", err);
    return false;
  }
}

async function testConfigDelete(): Promise<boolean> {
  try {
    const res = await post("/api/v1/config", {
      operation: "delete",
      keys: ["test"],
    });
    log("config/delete", res);

    // Verify it's gone
    const check = await post("/api/v1/config", {
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
  } catch (err) {
    fail("Config delete", err);
    return false;
  }
}

async function testPushFlowConfig(): Promise<boolean> {
  try {
    // Push a flow definition that LLM services will pick up
    const res = await post("/api/v1/config", {
      operation: "put",
      keys: ["flows"],
      values: {
        default: {
          topics: {
            request: "tg.flow.text-completion-request",
            response: "tg.flow.text-completion-response",
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
  } catch (err) {
    fail("Flow config push", err);
    return false;
  }
}

async function testTextCompletion(): Promise<boolean> {
  try {
    console.log("\n  Sending text-completion request (may take a few seconds)...");
    // Use model from env or default to qwen2.5:0.5b (Ollama-compatible)
    const model = process.env.LLM_MODEL ?? "qwen2.5:0.5b";
    const res = await post("/api/v1/flow/default/service/text-completion", {
      system: "You are a helpful assistant. Reply in one sentence.",
      prompt: "What is 2+2?",
      model,
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
  } catch (err) {
    fail("Text completion", err);
    return false;
  }
}

async function testWebSocket(): Promise<boolean> {
  try {
    // Use the vendored client's WebSocket adapter
    const { getWebSocketConstructor } = await import(
      "../packages/client/src/socket/websocket-adapter.js"
    );
    const WS = getWebSocketConstructor();

    return new Promise<boolean>((resolve) => {
      const ws = new WS(`${GATEWAY_URL.replace("http", "ws")}/api/v1/socket`);
      const timeout = setTimeout(() => {
        ws.close();
        fail("WebSocket", "connection timeout");
        resolve(false);
      }, 5000);

      ws.onopen = () => {
        clearTimeout(timeout);
        // Send a config list request
        const msg = JSON.stringify({
          id: "test-ws-1",
          service: "config",
          request: { operation: "list", keys: [] },
        });
        ws.send(msg);
      };

      ws.onmessage = (event: { data: unknown }) => {
        clearTimeout(timeout);
        const data = JSON.parse(String(event.data));
        log("websocket/response", data);
        ws.close();
        if (data.id === "test-ws-1") {
          pass("WebSocket round-trip works");
          resolve(true);
        } else {
          fail("WebSocket", "unexpected response id");
          resolve(false);
        }
      };

      ws.onerror = (err: unknown) => {
        clearTimeout(timeout);
        fail("WebSocket", err);
        resolve(false);
      };
    });
  } catch (err) {
    fail("WebSocket", err);
    return false;
  }
}

// ─── Main ─────────────────────────────────────────────────────────────

async function main(): Promise<void> {
  console.log("╔══════════════════════════════════════════════════╗");
  console.log("║  TrustGraph TypeScript — Integration Test       ║");
  console.log("╚══════════════════════════════════════════════════╝");
  console.log(`\nGateway: ${GATEWAY_URL}`);

  // Check gateway is reachable
  try {
    const res = await fetch(`${GATEWAY_URL}/api/v1/metrics`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    pass("Gateway reachable");
  } catch (err) {
    fail("Gateway reachable", err);
    console.error("\n⚠ Gateway not running. Start it first:");
    console.error("  pnpm tsx scripts/run-gateway.ts");
    process.exit(1);
  }

  let passed = 0;
  let failed = 0;
  const run = async (name: string, fn: () => Promise<boolean>) => {
    console.log(`\n── ${name} ──`);
    if (await fn()) passed++;
    else failed++;
  };

  // Config CRUD tests
  await run("Config List", testConfigList);
  await run("Config Put", testConfigPut);
  await run("Config Get", testConfigGet);
  await run("Config Delete", testConfigDelete);

  // WebSocket test
  await run("WebSocket Round-Trip", testWebSocket);

  // Flow config push
  await run("Push Flow Config", testPushFlowConfig);

  // LLM test (only if a running LLM service is available)
  if (process.env.SKIP_LLM !== "1") {
    console.log("\n  (Testing text-completion — set SKIP_LLM=1 to skip)");
    await run("Text Completion", testTextCompletion);
  } else {
    console.log("\n  (SKIP_LLM=1 — skipping LLM test)");
  }

  console.log("\n══════════════════════════════════════════════════");
  console.log(`  Results: ${passed} passed, ${failed} failed`);
  console.log("══════════════════════════════════════════════════\n");

  process.exit(failed > 0 ? 1 : 0);
}

main();
