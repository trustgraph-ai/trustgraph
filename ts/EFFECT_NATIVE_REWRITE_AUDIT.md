# TrustGraph Effect-Native Rewrite Opportunity Audit

This is the current backlog snapshot for the playbook in
`ts/EFFECT_NATIVE_REWRITE_PLAYBOOK.md`. The branch is `ts-port-effect-v4`.
The unrelated local file `.idea/effect.intellij.xml` must stay uncommitted.

## Inputs

Verified source roots:

- TrustGraph TS port: `/home/elpresidank/YeeBois/dev/trustgraph/ts`
- Effect v4 subtree: `/home/elpresidank/YeeBois/projects/beep-effect2/.repos/effect-v4`
- Installed Effect beta used by this workspace: `ts/node_modules/effect`

Current signal counts from `ts/packages` after the 2026-06-02 Librarian
schema/assertion cleanup slice:

| Signal | Count |
| --- | ---: |
| `Effect.runPromise` | 204 |
| `Map<` | 74 |
| `WebSocket` | 47 |
| `new Map` | 56 |
| `toPromiseRequestor` | 0 |
| `makeAsyncProcessor` | 19 |
| `receive(` | 18 |
| `while (` | 10 |
| `new Error` | 14 |
| `new Promise` | 10 |
| `JSON.parse` | 7 |
| `localStorage` | 9 |
| `JSON.stringify` | 6 |
| `setTimeout` | 4 |
| `process.env` | 3 |

Notes:

- The remaining `process.env` hits are in `packages/workbench/playwright.config.ts`.
- In production `packages/base`, `packages/cli`, and `packages/mcp` sources,
  the strict scans for `new Error`, `new Promise`, `setTimeout`,
  `JSON.parse`, `JSON.stringify`, and direct `process.env` reads are clean.
- `Effect.runPromise` is expected at external Promise compatibility
  boundaries, but each match should still be audited for avoidable internal
  runtime ownership.
- The `Effect.runPromise`, `Map<`, and `new Map` counts increased in this
  snapshot because the FlowManager slice added focused service tests and
  Promise compatibility facades while removing the service's internal mutable
  object state.
- The remaining `Record<string, any>` hit is the librarian service object and
  should be removed in the next librarian state migration slice.

## Loop Passes

### 2026-06-02: Base Request/Response Facade

- Status: migrated and verified.
- Completed:
  - Request/response startup now owns a scoped Effect runtime handle and maps
    failures to TrustGraph tagged messaging errors.
  - Runtime shutdown is idempotent and uses scoped fibers.
  - Tests cover Promise compatibility, tagged timeout errors, and tagged
    lifecycle errors.
- Verification:
  - `bun run --cwd ts/packages/base test`
  - `bun run --cwd ts/packages/base build`
  - `bun run --cwd ts check:tsgo`
  - `bun run --cwd ts build`
  - `bun run --cwd ts test`

### 2026-06-02: Gateway Dispatcher Requestor Cache

- Status: migrated and package-verified.
- Completed:
  - Gateway dispatcher caches scoped `EffectRequestResponse` handles instead
    of `Promise<RequestResponse>` values.
  - Lazy requestor creation is serialized with `SynchronizedRef.modifyEffect`.
  - Streaming final-marker detection is centralized.
  - Dispatcher cleanup uses Effect scope/error handling instead of manual
    `try`/`catch`.
- Verification:
  - `bun run --cwd ts/packages/flow test`
  - `bun run --cwd ts/packages/flow build`
  - `bun run --cwd ts check:tsgo`

### 2026-06-02: Strict Base, CLI, MCP, And tsgo Slice

- Status: migrated, root-verified, committed, and pushed.
- Completed:
  - Base messaging, NATS backend, producer, consumer, subscriber,
    request/response, runtime factories, processor programs, flow specs, and
    LLM service now use Effect-native boundaries, schema codecs, scoped
    cleanup, and `S.TaggedErrorClass.make(...)` errors.
  - CLI commands now run Effect programs at the command boundary, wrap socket
    lifecycle with `Effect.acquireUseRelease`, encode JSON through Effect
    Schema, and write output without `console.log`.
  - MCP Effect server now loads env/config through `Config`, wraps gateway
    calls with `Effect.tryPromise`, constructs schema classes with `.make`, and
    uses tagged errors.
  - MCP stdio compatibility server keeps `createMcpServer` and `run`, but uses
    Effect callbacks/tryPromise/schema encoding internally. `run()` uses
    `ManagedRuntime`; `runMain()` uses `NodeRuntime.runMain`.
  - Flow stateful service launch sites now pass an explicit `Context.Context`
    into the base processor runtime instead of hiding requirements behind
    assertions.
- Verification:
  - `cd ts && bun run check`
  - `cd ts && bun run test`
  - `cd ts && bun run build`
  - `git diff --check`

### 2026-06-02: ConfigService Ref-Backed State Slice

- Status: migrated and root-verified.
- Completed:
  - `ts/packages/flow/src/config/service.ts` now models runtime state as a
    `SynchronizedRef<ConfigServiceState>` instead of adding mutable
    `store`, `version`, consumer, and producer fields onto the processor
    object.
  - Config operations have Effect-returning handlers with Promise facades only
    on the exported compatibility methods.
  - Request narrowing now uses `effect/Predicate` rather than request-record
    type assertions.
  - Persistence remains schema-backed and now reads/writes snapshots from the
    ref-backed state.
  - The consume loop now uses `Effect.whileLoop`; the remaining
    `consumer.receive(2000)` call is a pubsub boundary for this service.
  - Service startup now exposes `runMain()` through `NodeRuntime.runMain`.
    The legacy `run()` Promise facade uses `ManagedRuntime`, and
    `ts/scripts/run-config.ts` delegates directly to `runMain()` instead of
    owning its own catch/process-exit wrapper.
  - Config-service tests cover tagged invalid mutation errors, workspace
    persistence, legacy load, concurrent ref-backed mutations, and push
    publishing from the stored producer handle.
- Verification:
  - `bun run --cwd ts/packages/flow build`
  - `bun run --cwd ts/packages/flow test`
  - `cd ts && bun run check`
  - `cd ts && bun run build`
  - `cd ts && bun run test`
  - `git diff --check`

### 2026-06-02: RAG And Agent Requestor Bridge Slice

- Status: migrated, root-verified, committed, and pushed.
- Completed:
  - `ts/packages/flow/src/retrieval/graph-rag.ts` and
    `ts/packages/flow/src/retrieval/document-rag.ts` now accept
    `EffectRequestResponse` clients directly. The engines no longer adapt
    Effect requestors back to Promise requestors and then wrap those calls in
    `Effect.tryPromise`.
  - `ts/packages/flow/src/retrieval/graph-rag-service.ts` and
    `ts/packages/flow/src/retrieval/document-rag-service.ts` now pass native
    flow requestors directly into the engines.
  - `ts/packages/flow/src/agent/react/tools.ts` now accepts
    `EffectRequestResponse` clients directly for graph RAG, document RAG,
    triples, and MCP tool calls. Tool input narrowing uses Schema and
    `effect/Predicate` rather than local request/response type assertions.
  - `ts/packages/flow/src/agent/react/service.ts` wires default and configured
    tools with native Effect requestors instead of `toPromiseRequestor`.
  - Graph RAG, document RAG, and agent service startup now expose `runMain()`
    through `NodeRuntime.runMain`; their legacy `run()` Promise facades use
    `ManagedRuntime`.
  - `ts/scripts/run-graph-rag.ts`, `ts/scripts/run-document-rag.ts`, and
    `ts/scripts/run-agent.ts` now delegate to `runMain()`.
- Verification:
  - `bun run --cwd ts/packages/flow build`
  - `bun run --cwd ts/packages/flow test`
  - `cd ts && bun run check`
  - `cd ts && bun run build`
  - `cd ts && bun run test`

### 2026-06-02: KnowledgeCore Ref-Backed State Slice

- Status: migrated and root-verified.
- Completed:
  - `ts/packages/flow/src/cores/service.ts` now exposes a typed
    `KnowledgeCoreService` instead of `AsyncProcessorRuntime & Record<string,
    any>`.
  - Runtime state now lives in
    `SynchronizedRef<KnowledgeCoreServiceState>` with `kgCores`, `deCores`,
    the request consumer, and response producer.
  - Knowledge operations now have Effect-returning handlers with Promise
    facades only on exported compatibility methods.
  - Persistence now decodes legacy and current snapshot shapes with Effect
    Schema and encodes JSON through Schema rather than raw
    `JSON.parse`/`JSON.stringify` plus assertions.
  - The consume loop now uses `Effect.whileLoop`; the remaining
    `consumer.receive(2000)` call is a pubsub boundary for this service.
  - The service exposes `runMain()` through `NodeRuntime.runMain`; legacy
    `run()` uses `ManagedRuntime`, and `ts/scripts/run-knowledge.ts` delegates
    to `runMain()`.
  - `ts/packages/base/src/schema/messages.ts` now models legacy hyphenated
    knowledge request/response aliases so the service can preserve the wire
    shape without response type assertions.
  - New knowledge-core tests cover ref-backed mutation, graph embedding alias
    responses, concurrent state updates, and legacy persistence loading.
- Verification:
  - `bun run --cwd ts/packages/base build`
  - `bun run --cwd ts/packages/flow build`
  - `bun run --cwd ts/packages/flow test`
  - `cd ts && bun run check`
  - `cd ts && bun run build`
  - `cd ts && bun run test`

### 2026-06-02: Flow Manager And Librarian Runtime Normalization

- Status: migrated and root-verified.
- Completed:
  - `ts/packages/flow/src/flow-manager/service.ts` and
    `ts/packages/flow/src/librarian/service.ts` now expose `runMain()` through
    `NodeRuntime.runMain`.
  - Their legacy `run()` Promise facades now use `ManagedRuntime` instead of
    directly owning `Effect.runPromise`.
  - `ts/scripts/run-flow-manager.ts` and `ts/scripts/run-librarian.ts` now
    delegate to `runMain()` instead of wrapping startup with local
    `.catch(console.error/process.exit)` handlers.
- Verification:
  - `bun run --cwd ts/packages/flow build`
  - `cd ts && bun run check`
  - `cd ts && bun run build`
  - `cd ts && bun run test`
  - `git diff --check`

### 2026-06-02: FlowManager Ref-Backed State Slice

- Status: migrated and root-verified.
- Completed:
  - `ts/packages/flow/src/flow-manager/service.ts` now exposes a typed
    `FlowManagerService` instead of `AsyncProcessorRuntime & Record<string,
    any>`.
  - Runtime state now lives in
    `SynchronizedRef<FlowManagerServiceState>` with `flows`, `blueprints`, the
    request consumer, response producer, and config request client.
  - Flow operations now have Effect-returning handlers with Promise facades
    only on exported compatibility methods.
  - Blueprint config loading now narrows runtime values before constructing
    `Blueprint` records, replacing the prior `parsed as Blueprint` shortcut.
  - `start-flow` and `stop-flow` mutate the flow map through
    `SynchronizedRef.modifyEffect`, making duplicate checks and map updates
    atomic.
  - The consume loop now uses `Effect.whileLoop`; the remaining
    `consumer.receive(2000)` call is a pubsub boundary for this service.
  - New flow-manager tests cover tagged errors, ref-backed flow mutation,
    config push/delete requests, blueprint narrowing, duplicate concurrent
    starts, and message-level flow-error responses.
- Verification:
  - `bun run --cwd ts/packages/flow test -- src/__tests__/flow-manager-service.test.ts`
  - `bun run --cwd ts/packages/flow build`
  - `bun run --cwd ts/packages/flow test`
  - `cd ts && bun run check`
  - `cd ts && bun run build`
  - `cd ts && bun run test`
  - `git diff --check`

### 2026-06-02: Librarian Schema And Assertion Cleanup Slice

- Status: migrated and root-verified.
- Completed:
  - `ts/packages/base/src/schema/messages.ts` now models librarian upload and
    stream request/response fields directly, instead of requiring service-side
    `as LibrarianResponse` casts for the existing wire protocol.
  - `ts/packages/flow/src/librarian/service.ts` now decodes persisted
    librarian state through a concrete `S.fromJsonString` schema instead of a
    generic JSON decode plus `as A`.
  - Document metadata `metadata` triples now narrow through Schema decoding
    with `Option` before being included in normalized metadata.
  - Upload, stream, and complete-upload request/response constructors now rely
    on the schema-modeled fields instead of local type assertions.
  - New librarian tests cover modeled upload fields, concrete persisted-state
    loading, and schema-backed metadata triple normalization.
- Remaining:
  - Librarian still has the dynamic `AsyncProcessorRuntime & Record<string,
    any>` service object and sync throw helper paths. Keep it as the next P0
    state/ref-backed migration.
- Verification:
  - `bun run --cwd ts/packages/base build`
  - `bun run --cwd ts/packages/flow build`
  - `bun run --cwd ts/packages/flow test -- src/__tests__/librarian-service.test.ts`
  - `bun run --cwd ts/packages/flow test`
  - `cd ts && bun run check`
  - `cd ts && bun run build`
  - `cd ts && bun run test`
  - `git diff --check`

## Subagent Findings To Preserve

- MCP/workbench:
  - Make the Effect MCP server the canonical implementation. The old stdio
    server should remain only as compatibility while parity is needed.
  - Workbench BaseApi atoms can move toward `AtomRpc` or `AtomHttpApi` after
    the client API is less Promise-first.
  - MCP env is now Config-backed; continue that policy for future MCP settings.
- Flow stateful services:
  - Config service, KnowledgeCore service, and FlowManager ref-backed state
    are complete. Librarian now has native Effect module startup
    (`NodeRuntime.runMain` with a `ManagedRuntime` compatibility facade), but
    it still has a mutable poller service object. It remains a good candidate
    for `Context` services, scoped layers, `Ref`/`SynchronizedRef`,
    `Schedule`, and managed persistence.
  - Persistence IO should move toward `FileSystem` or `KeyValueStore` where
    the installed beta has the needed provider surface.
- Base messaging/processors:
  - Subscriber queues/maps, processor/flow Promise compatibility, and dynamic
    flow state should continue moving toward `Queue`, `Deferred`,
    `SynchronizedRef`, `Schedule`, and scoped layers.
  - Existing constructor shims and typed registries in base processors still
    use type assertions; they need a typed factory/registry redesign rather
    than more assertions.
- Gateway/client:
  - Knowledge streams still duplicate legacy end-of-stream handling.
  - Effect RPC client remains Promise-first internally in places and should be
    turned into a managed runtime or scoped layer.
  - WebSocket adapter shims still contain host-boundary `try`/`catch` and
    normal `Error` construction.
- RAG/providers/storage:
  - RAG and agent requestor bridges are complete: `toPromiseRequestor` has no
    remaining `ts/packages` matches.
  - Provider SDKs and storage clients should become managed resources where
    they have meaningful lifecycle.
  - FalkorDB/Qdrant/Ollama/OpenAI-compatible surfaces still need config,
    schema, and scope audits.

## Ranked Findings

### P0: Migrate Librarian Stateful Service To Scoped Effect Service

- TrustGraph evidence:
  - `ts/packages/flow/src/librarian/service.ts`
- Effect primitives:
  - `Context`, `Layer.scoped`, `Ref`, `SynchronizedRef`, `Schedule`,
    `Effect.addFinalizer`, `Config`, `Schema`, `FileSystem`,
    `KeyValueStore`.
- Rewrite shape:
  - Model one remaining service at a time as a `Context` service plus scoped
    layer or ref-backed state slice.
  - Store mutable service state in `Ref` or `SynchronizedRef`.
  - Run service main programs with platform runtime entrypoints such as
    `NodeRuntime.runMain`; keep `ManagedRuntime` only for compatibility
    Promise facades.
  - Replace polling sleep loops with schedules where behavior allows.
  - Decode persisted payloads and config with schemas at boundaries.
- Tests:
  - Service-specific tests plus `cd ts && bun run --cwd packages/flow test`.

### P1: Finish Client RPC Boundary Modernization

- TrustGraph evidence:
  - `ts/packages/client/src/socket/effect-rpc-client.ts`
  - `ts/packages/client/src/socket/trustgraph-socket.ts`
  - `ts/packages/client/src/socket/websocket-adapter.ts`
- Effect primitives:
  - `effect/unstable/socket` `Socket.makeWebSocket`, `fromWebSocket`,
    `toChannel`, `layerWebSocket`.
  - `effect/unstable/rpc/RpcClient.layerProtocolSocket`.
  - `effect/unstable/rpc/RpcSerialization.layerNdjson` or `layerNdJsonRpc`.
  - `ManagedRuntime` for compatibility facades when a Promise API must remain.
- Rewrite shape:
  - Treat `EffectRpcClient` as an internal managed runtime or scoped layer.
  - Expose Promise-returning methods through a thin adapter.
  - Replace normal client `Error` constructors with tagged errors before they
    cross into shared Effect code.
- Tests:
  - `cd ts && bun run --cwd packages/client test`

### P1: Base Processor Registry And Constructor Shims

- TrustGraph evidence:
  - `ts/packages/base/src/processor/async-processor.ts`
  - `ts/packages/base/src/processor/flow.ts`
  - `ts/packages/base/src/processor/flow-processor.ts`
- Effect primitives:
  - Schema-backed registries, `Context`, `Layer`, `Effect.fn`, `Option`,
    `Predicate`.
- Rewrite shape:
  - Replace constructor `as unknown as` shims with typed factory exports.
  - Replace resource lookup casts with schema-backed typed registry helpers.
  - Do not add assertions to quiet Effect channel inference problems.
- Tests:
  - `cd ts && bun run --cwd packages/base test`
  - Root `cd ts && bun run check` because this surface easily pollutes Effect
    error and requirement channels.

### P1: Make SDK, Storage, And Provider Layers Managed Resources

- TrustGraph evidence:
  - `ts/packages/flow/src/storage/triples/falkordb.ts`
  - `ts/packages/flow/src/storage/embeddings/qdrant-graph.ts`
  - `ts/packages/flow/src/storage/embeddings/qdrant-doc.ts`
  - `ts/packages/flow/src/model/text-completion/*.ts`
  - `ts/packages/flow/src/embeddings/ollama.ts`
- Effect primitives:
  - `Effect.acquireRelease`, `Layer.scoped`, `Config`, `ConfigProvider`,
    `Metric`, `Logger`, Effect AI provider layers.
- Rewrite shape:
  - Move env/config reading into `Config` loaders and provider-specific layers.
  - Scope SDK clients that need explicit close/disconnect.
  - Remove `Effect.void as Effect.Effect<undefined>` stream assertions by
    letting branch return types infer or by restructuring the stream parser.
- Tests:
  - Provider config tests with `ConfigProvider.fromMap`.
  - Storage tests with fake clients before changing real resource lifetimes.

### P2: Canonicalize MCP Around The Effect Server

- Status:
  - First blocker slice complete: MCP now builds under strict tsgo and the
    stdio server has an Effect-backed compatibility implementation.
- Remaining shape:
  - Decide whether the old SDK/Zod stdio compatibility surface should stay as
    a wrapper or be removed.
  - Add parity tests before deleting any public entry point.
- Tests:
  - `cd ts && bun run --cwd packages/mcp build`
  - Root `cd ts && bun run check`

### P2: Tighten Workbench Platform And Reactivity Usage

- TrustGraph evidence:
  - `ts/packages/workbench/src/atoms/workbench.ts`
  - Remaining direct browser state includes `localStorage` and DOM theme
    inspection.
- Effect primitives:
  - `BrowserKeyValueStore.layerLocalStorage`,
    `BrowserKeyValueStore.layerSessionStorage`, `BrowserHttpClient`,
    `Clipboard`, `AtomRpc`, `AtomHttpApi`, `AtomRegistry`, `AsyncResult`,
    `Reactivity`.
- Rewrite shape:
  - Leave workbench out of the next backend/runtime rewrite wave.
  - Move persistent UI state through browser platform services later.
- Tests:
  - `cd ts && bun run workbench:qa`

## Recommended PR Order

1. Librarian or flow-manager scoped state migration.
2. Client RPC managed runtime/scoped layer cleanup.
3. Base processor registry and constructor shim redesign.
4. Gateway RPC callback and client streaming completion cleanup.
5. Storage/provider managed resource cleanup.
6. MCP parity/deletion decision and workbench platform polish.

## No-Op Rules

Do not flag these as rewrite blockers without additional proof:

- Promise-returning CLI actions, MCP SDK callbacks, client compatibility
  methods, and Fastify route handlers at true external boundaries. Boundary
  code still must map failures into typed errors or wire errors.
- `try`/`catch` blocks at host/tool boundaries only when the catch maps into a
  typed error or a wire-contract error. Internal exception capture should use
  `Effect.try`, `Effect.tryPromise`, or `Result.try`.
- `S.Class`, `S.TaggedErrorClass`, `Context.Service`, `Rpc.make`, and
  `HttpApi.make` when they are required or idiomatic for the Effect API.
- Plain `Map` usage for local pure transformations, such as graph utility
  construction, unless the state is long-lived mutable service state.
- JSON stringification in tests or wire-contract fixtures. Production JSON
  encode/decode should prefer schema codecs when the encoded form can be
  preserved.

## Acceptance For Final Loop Completion

The overall playbook loop is complete only when:

- All remaining playbook signal matches are migrated or documented as no-op
  external-boundary cases with concrete evidence.
- No P0/P1/P2 migration item remains in this audit.
- `cd ts && bun run check`, `cd ts && bun run build`, `cd ts && bun run test`,
  and `git diff --check` pass after the final migration slice.
