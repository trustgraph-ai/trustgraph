# TrustGraph Effect-Native Rewrite Opportunity Audit

This is the first ranked audit produced from the playbook in
`ts/EFFECT_NATIVE_REWRITE_PLAYBOOK.md`. It is an opportunity map, not a code
rewrite. The branch was `ts-port-effect-v4`; the only unrelated local file seen
during the audit was `.idea/effect.intellij.xml`.

## Inputs

Verified source roots:

- TrustGraph TS port: `/home/elpresidank/YeeBois/dev/trustgraph/ts`
- Effect v4 subtree: `/home/elpresidank/YeeBois/projects/beep-effect2/.repos/effect-v4`
- Reactivity fallback: `ts/node_modules/effect/src/unstable/reactivity`
- Atom React fallback: `ts/packages/workbench/node_modules/@effect/atom-react`

Signal counts from `ts/packages`:

| Signal | Count |
| --- | ---: |
| `Effect.runPromise` | 71 |
| `Map<` | 54 |
| `JSON.stringify` | 50 |
| `WebSocket` | 45 |
| `process.env` | 44 |
| `new Map` | 42 |
| `toPromiseRequestor` | 19 |
| `makeAsyncProcessor` | 19 |
| `new Promise` | 18 |
| `JSON.parse` | 16 |
| `receive(` | 16 |
| `setTimeout` | 13 |
| `while (` | 10 |
| `localStorage` | 8 |

## Ranked Findings

### P0: Collapse Base Messaging Promise Facades

- Impact: 5
- Risk: 4
- Confidence: 4
- TrustGraph evidence:
  - `ts/packages/base/src/messaging/runtime.ts` already defines Effect
    producer, consumer, request/response factories, queues, fibers, and scopes.
  - `ts/packages/base/src/messaging/consumer.ts` still has a manual
    `while (running)` receive loop, `sleep`, and Promise delay helpers.
  - `ts/packages/base/src/messaging/subscriber.ts` still manages resolver maps
    and timeout promises.
  - `ts/packages/base/src/processor/flow.ts` exposes compatibility scope
    helpers and converts Effect handles back into Promise-style handles.
- Effect evidence:
  - `effect/Queue`, `effect/PubSub`, `effect/Stream`, `effect/Scope`,
    `effect/Layer`, `effect/Schedule`, `effect/Ref`.
  - Sources: `packages/effect/src/Queue.ts`, `PubSub.ts`, `Stream.ts`,
    `Scope.ts`, `Layer.ts`, `Schedule.ts`, `Ref.ts`.
- Rewrite shape:
  - Make the Effect runtime factories the canonical internal surface.
  - Keep Promise adapters only at external compatibility boundaries.
  - Replace polling sleep loops with scheduled scoped consumers where possible.
  - Replace resolver maps with `Queue`, `Deferred`, or `PubSub`-backed routing.
- Tests:
  - `cd ts && bun run --cwd packages/base test`
  - Existing runtime tests around request/response, flow specs, and consumers
    should be expanded before removing compatibility behavior.
- Blockers:
  - Public package exports may still expect Promise-shaped producer, consumer,
    and request/response handles. Inventory callers before changing exports.

### P0: Convert Stateful Flow Services To Scoped Effect Services

- Impact: 5
- Risk: 4
- Confidence: 4
- TrustGraph evidence:
  - `ts/packages/flow/src/config/service.ts` uses `makeAsyncProcessor`,
    mutable nested `Map` state, `while (this.running)`, `receive(2000)`,
    `sleep`, JSON persistence, and direct `process.env`.
  - `ts/packages/flow/src/librarian/service.ts`, `cores/service.ts`, and
    `flow-manager/service.ts` repeat the same service-object pattern.
- Effect evidence:
  - `Context`, `Layer.scoped`, `Ref`, `SynchronizedRef`, `Schedule`,
    `Effect.addFinalizer`, `Config`, `Schema`, `effect/FileSystem`,
    `effect/unstable/persistence/KeyValueStore`.
  - Sources: `packages/effect/src/Context.ts`, `Layer.ts`, `Ref.ts`,
    `SynchronizedRef.ts`, `Schedule.ts`, `Config.ts`, `Schema.ts`,
    `ts/node_modules/effect/src/FileSystem.ts`,
    `ts/node_modules/effect/src/unstable/persistence/KeyValueStore.ts`.
- Rewrite shape:
  - Model each service as a `Context` service plus a scoped layer.
  - Store service state in `Ref` or `SynchronizedRef`, not mutable object fields.
  - Express persistence with `effect/FileSystem` or
    `KeyValueStore.layerFileSystem` when the installed beta exposes the needed
    provider.
  - Decode persisted payloads and config with schemas at boundaries.
- Tests:
  - Service-specific tests plus `cd ts && bun run --cwd packages/flow test`.
  - Add persistence round-trip tests before replacing file IO.
- Blockers:
  - These services are behavior-heavy. Do one service per PR after the shared
    runtime surface is stable.

### P0: Make Gateway Dispatcher Effect-Native

- Impact: 5
- Risk: 3
- Confidence: 4
- TrustGraph evidence:
  - `ts/packages/flow/src/gateway/server.ts` already builds RPC/WebSocket
    pieces with Effect.
  - `ts/packages/flow/src/gateway/rpc-server.ts` uses `Queue` and RPC layers.
  - `ts/packages/flow/src/gateway/dispatch/manager.ts` still keeps
    `Map<string, Promise<RequestResponse<unknown, unknown>>>`, manual
    streaming completion checks, and per-publish producer construction.
- Effect evidence:
  - `effect/unstable/rpc` `RpcClient`, `RpcServer`, `RpcSerialization`.
  - `effect/unstable/socket` `Socket`.
  - `effect/Queue`, `Stream`, `Scope`, `Layer`.
  - Sources: `ts/node_modules/effect/src/unstable/rpc/RpcClient.ts`,
    `RpcServer.ts`, `RpcSerialization.ts`, and
    `ts/node_modules/effect/src/unstable/socket/Socket.ts`.
- Rewrite shape:
  - Convert dispatcher manager methods to Effect-returning functions internally.
  - Cache requestors as scoped resources instead of Promise values.
  - Represent streaming dispatch as `Stream` or `Queue` instead of callback
    completion detection where the wire protocol allows it.
  - Keep Fastify route handlers as Promise boundaries.
- Tests:
  - Gateway dispatch tests with fake pubsub.
  - `cd ts && SKIP_LLM=1 bun run test:pipeline` after implementation.
- Blockers:
  - The gateway is an integration boundary. Preserve current HTTP and WebSocket
    wire behavior during the first rewrite.

### P1: Remove RAG And Agent `toPromiseRequestor` Bridges

- Impact: 4
- Risk: 3
- Confidence: 5
- TrustGraph evidence:
  - `ts/packages/flow/src/retrieval/document-rag-service.ts`
  - `ts/packages/flow/src/retrieval/graph-rag-service.ts`
  - `ts/packages/flow/src/agent/react/service.ts`
  - All define `toPromiseRequestor` and then immediately adapt Effect
    requestors back to Promise-style clients.
- Effect evidence:
  - Existing TrustGraph `EffectRequestResponse` in
    `ts/packages/base/src/messaging/runtime.ts`.
  - `effect/Stream`, `Effect.fn`, `Effect.runPromiseWith` for boundary-only
    execution.
- Rewrite shape:
  - Update RAG engines and agent helpers to accept Effect requestors or
    functions returning `Effect`.
  - Keep Promise wrappers only for old public APIs or tests that explicitly
    verify compatibility.
  - Convert streaming agent flows to `Stream` where possible.
- Tests:
  - Existing RAG and agent service tests.
  - Add tests that assert requestor errors stay typed through the Effect path.
- Blockers:
  - Engine call signatures need a small design pass so RAG and agent rewrite in
    the same direction.

### P1: Finish Client RPC Boundary Modernization

- Impact: 4
- Risk: 3
- Confidence: 4
- TrustGraph evidence:
  - `ts/packages/client/src/socket/effect-rpc-client.ts` already uses
    `Socket.makeWebSocket`, `RpcClient.layerProtocolSocket`, and
    `RpcSerialization.layerNdjson`.
  - The same file still owns `scopePromise`, `clientPromise`, repeated
    `Effect.runPromise`, listener sets, a WebSocket constructor shim, and a
    Promise facade.
  - `ts/packages/client/src/socket/trustgraph-socket.ts` is mostly a
    compatibility API over the Effect RPC client.
- Effect evidence:
  - `effect/unstable/socket/Socket`: `makeWebSocket`, `fromWebSocket`,
    `toChannel`, `layerWebSocket`.
  - `effect/unstable/rpc/RpcClient`: `layerProtocolSocket`.
  - `effect/unstable/rpc/RpcSerialization`: `layerNdjson`, `layerNdJsonRpc`.
- Rewrite shape:
  - Treat `EffectRpcClient` as an internal managed runtime or scoped layer.
  - Expose Promise-returning methods only through a thin compatibility adapter.
  - Move browser vs Node WebSocket constructor selection into platform layers.
- Tests:
  - `cd ts && bun run --cwd packages/client test`
  - Keep timeout/retry tests around `withDispatchRequestPolicy`.
- Blockers:
  - Workbench and CLI still consume Promise-shaped client APIs.

### P1: Make SDK, Storage, And Provider Layers Managed Resources

- Impact: 4
- Risk: 3
- Confidence: 3
- TrustGraph evidence:
  - `ts/packages/flow/src/storage/triples/falkordb.ts`
  - `ts/packages/flow/src/storage/embeddings/qdrant-graph.ts`
  - `ts/packages/flow/src/storage/embeddings/qdrant-doc.ts`
  - `ts/packages/flow/src/model/text-completion/*.ts`
  - These files create direct SDK clients and read `process.env` in live
    constructors.
- Effect evidence:
  - `Effect.acquireRelease`, `Layer.scoped`, `Config`, `ConfigProvider`,
    `effect/FileSystem`, `effect/unstable/persistence/KeyValueStore`,
    `Metric`, `Logger`.
  - AI provider modules from installed provider packages, with subtree source
    proof under `packages/ai/*/src`, including `OpenAiLanguageModel.ts`,
    `AnthropicLanguageModel.ts`, and `OpenRouterLanguageModel.ts`.
- Rewrite shape:
  - Move env reading into `Config` loaders and provider-specific layers.
  - Scope SDK clients that need explicit close/disconnect.
  - Replace `console` or ad hoc logging with `Effect.log*` and metrics where
    useful.
- Tests:
  - Provider config tests with `ConfigProvider.fromMap`.
  - Storage tests with fake clients before changing real resource lifetimes.
- Blockers:
  - Some third-party SDK clients may not have meaningful finalizers. Mark those
    no-op after proof instead of forcing fake lifecycle code.

### P2: Canonicalize MCP Around The Effect Server

- Impact: 3
- Risk: 2
- Confidence: 5
- TrustGraph evidence:
  - `ts/packages/mcp/src/server.ts` is the old SDK/Zod server.
  - `ts/packages/mcp/src/server-effect.ts` has Effect AI tools, schemas,
    `McpServer`, HTTP API integration, and provider layers.
- Effect evidence:
  - `effect/unstable/ai` `Tool`, `Toolkit`, `McpServer`, `McpSchema`,
    `LanguageModel`.
  - Sources: `ts/node_modules/effect/src/unstable/ai/Tool.ts`,
    `Toolkit.ts`, `McpServer.ts`, `McpSchema.ts`, `LanguageModel.ts`.
- Rewrite shape:
  - Do not rewrite the Effect server from scratch.
  - Make the Effect server canonical after parity checks.
  - Keep the old server only as compatibility or delete it once entrypoints and
    tests prove the Effect path is complete.
- Tests:
  - MCP package build/test.
  - Tool parity diff against `server.ts` before removal.
- Blockers:
  - Needs a policy decision about old SDK server lifetime.

### P2: Tighten Workbench Platform And Reactivity Usage

- Impact: 3
- Risk: 2
- Confidence: 4
- TrustGraph evidence:
  - `ts/packages/workbench/src/atoms/workbench.ts` already uses Atom,
    AsyncResult, Reactivity, browser layers, and metrics.
  - Remaining direct browser state includes `localStorage` reads/writes and DOM
    theme inspection.
- Effect evidence:
  - `BrowserKeyValueStore.layerLocalStorage`,
    `BrowserKeyValueStore.layerSessionStorage`, `BrowserHttpClient`,
    `Clipboard`.
  - `AtomRpc`, `AtomHttpApi`, `AtomRegistry`, `AsyncResult`, `Reactivity`.
- Rewrite shape:
  - Leave the workbench out of the first rewrite wave.
  - Later, move persistent UI state through `BrowserKeyValueStore` and keep
    remote state in Atom RPC/HTTP API families if the client API becomes fully
    typed Effect RPC.
- Tests:
  - `cd ts && bun run workbench:qa`.
- Blockers:
  - Workbench is already the most modern surface. Backend/runtime wins should
    happen first.

## Recommended PR Order

1. Base messaging/runtime convergence design and tests.
2. Gateway dispatcher internal Effect conversion.
3. RAG and agent requestor bridge removal.
4. One stateful Flow service conversion, starting with config or cores.
5. Client compatibility facade tightening.
6. Storage/provider managed resource cleanup.
7. MCP canonicalization and Workbench polish.

## No-Op Rules

Do not flag these as rewrite blockers without additional proof:

- Promise-returning CLI actions and Fastify route handlers at external
  boundaries.
- `S.Class`, `S.TaggedErrorClass`, `Context.Service`, `Rpc.make`, and
  `HttpApi.make` when they are required or idiomatic for the Effect API.
- Plain `Map` usage for local pure transformations, such as graph utility
  construction, unless the state is long-lived, mutable service state.
- JSON stringification that is part of the TrustGraph wire contract, unless a
  schema codec can preserve the exact encoded form.

## Acceptance

This audit is complete when:

- `ts/EFFECT_NATIVE_REWRITE_PLAYBOOK.md` exists.
- This ranked audit exists and cites concrete TrustGraph and Effect surfaces.
- `git diff --check` passes for both files.
- No code rewrite is mixed into this audit.
