# TrustGraph Effect-Native Rewrite Opportunity Audit

This is the current backlog snapshot for the playbook in
`ts/EFFECT_NATIVE_REWRITE_PLAYBOOK.md`. The branch is `ts-port-effect-v4`.
The unrelated local file `.idea/effect.intellij.xml` must stay uncommitted.

## Inputs

Verified source roots:

- TrustGraph TS port: `/home/elpresidank/YeeBois/dev/trustgraph/ts`
- Effect v4 subtree: `/home/elpresidank/YeeBois/projects/beep-effect2/.repos/effect-v4`
- Installed Effect beta used by this workspace: `ts/node_modules/effect`

Current signal counts from `ts/packages` after the 2026-06-02 client RPC
acquisition cause tap slice:

| Signal | Count |
| --- | ---: |
| `Effect.runPromise` | 172 |
| `Effect.runPromiseWith` | 0 |
| `Effect.cached` | 0 |
| `Layer.succeed` | 18 |
| `Map<` | 82 |
| `WebSocket` | 62 |
| `new Map` | 60 |
| `toPromiseRequestor` | 0 |
| `makeAsyncProcessor` | 19 |
| `receive(` | 17 |
| `while (` | 2 |
| `new Error` | 8 |
| `new Promise` | 10 |
| `JSON.parse` | 4 |
| `localStorage` | 8 |
| `JSON.stringify` | 7 |
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
- The `Map<` and `new Map` counts increased in this snapshot because the
  Librarian slice introduced explicit ref-backed state types and clone helpers
  while removing the service object's direct mutable maps/handles.
- The `Effect.runPromise` and `WebSocket` counts dropped in this snapshot
  because `EffectRpcClient` now owns its RPC/socket layer with
  `ManagedRuntime` and uses Effect's WebSocket constructor layer.
- The raw `WebSocket` count increased in this snapshot because the adapter
  slice added focused tests and typed adapter names; production
  `websocket-adapter.ts` is now clean of `try`/`catch`, normal `Error`, and
  the previous constructor assertions.
- The `new Error` count dropped because `websocket-adapter.ts` now throws
  `S.TaggedErrorClass` adapter errors.
- The latest client socket slice removed the remaining production
  `trustgraph-socket.ts` normal `Error`, raw `JSON.parse`, and listener
  `try`/`catch` matches. The remaining client socket modernization signal is
  the shared `newableFactory` constructor assertion pattern.
- The service entrypoint runtime slice dropped the `Effect.runPromise` count by
  replacing remaining flow service `run()` program facades with
  `ManagedRuntime` and routing local `ts/scripts/run-*` launchers through
  `runMain()`/`NodeRuntime.runMain`.
- The base processor compatibility runtime slice dropped the
  `Effect.runPromise` count again by moving `AsyncProcessor`, `Flow`, and
  `FlowProcessor` Promise compatibility facades onto `ManagedRuntime`.
- The base flow definition schema slice removed hand-rolled
  `Predicate`/object narrowing from `flow-processor.ts`; signal counts are
  unchanged because this was a validation-quality migration.
- The text completion stream sentinel slice removed the duplicated
  `Effect.void as Effect.Effect<undefined>` assertions from provider stream
  unfold branches. Counts are unchanged because this was an Effect diagnostic
  and type-channel cleanup.
- The text completion generator boundary slice removed the
  `Effect.runPromise(Effect.fail(...))` fallback and the related
  `AsyncGenerator`/`IteratorResult` assertions from
  `model/text-completion/common.ts`.
- The text completion provider status slice replaced manual status/statusCode
  record assertions with `effect/Predicate` narrowing.
- The base parameter spec accessor slice added Schema-backed
  `ParameterSpec<T>` values plus `flow.parameterEffect(spec)` and
  `flow.parameter(spec)`. Bare string parameter lookup remains available as an
  `unknown` compatibility escape, while typed parameter access now decodes
  through Schema and fails with a tagged `FlowParameterDecodeError`.
- The base producer/requestor spec accessor slice added typed spec-object
  accessors for `ProducerSpec<T>` and `RequestResponseSpec<TReq, TRes>`, then
  migrated flow service producer/requestor lookups off caller-chosen generic
  string calls. Spec object handles are scoped per `Flow` through WeakMaps and
  finalizers delete only the handle they registered.
- The native PubSub boundary slice removed the unused legacy
  `messaging/subscriber.ts` async queue/fanout implementation. Effect's native
  `PubSub` is an in-process hub and does not replace the broker-backed
  `PubSubBackend`/NATS boundary, but it should be preferred for future
  in-process broadcast/fanout needs.
- The gateway streaming callback slice added Effect-returning dispatcher
  streaming methods, switched the RPC stream server off nested
  `Effect.runPromiseWith(context)` queue offers, and replaced the client
  `StopStreaming` sentinel error with `Stream.runForEachWhile`.
- The FalkorDB scoped client lifecycle slice removed the remaining
  `Effect.cached` matches from `ts/packages`. FalkorDB triples store/query
  Live layers and direct compatibility factories now acquire clients through
  `Effect.acquireRelease` and disconnect them on scope close. The
  `Effect.runPromise` count increased by two because the new lifecycle tests
  run scoped programs at the test boundary.
- The Qdrant config/schema/fakeability slice removed direct production
  `new QdrantClient`, sync config loading, payload casts, and Qdrant
  `Layer.succeed` service construction from graph/doc store/query modules.
  The installed Qdrant client exposes no public close/disconnect method, so
  this remains a fakeable construction and Schema decode slice rather than a
  scoped finalizer slice. `Effect.runPromise` increased because the new tests
  and legacy service initialization logs run Effects at compatibility
  boundaries.
- The client streaming facade slice did not change signal counts. It
  centralized the legacy streaming `{ response, complete, error }` envelope
  decode in `trustgraph-socket.ts`, uses Schema plus `effect/Predicate`
  property narrowing for streaming payload reads, and leaves service-specific
  legacy completion markers only where they preserve public callback behavior.
- The Ollama embeddings effectful layer slice dropped one `Layer.succeed`
  match by making `OllamaEmbeddingsLive` effectful and mapping config/load
  failures to `EmbeddingsError`. The `JSON.stringify` count increased by one
  because the new layer test uses a JSON response fixture.
- The text completion provider stream helper slice removed all provider-local
  `Stream.unfold` pull loops, dropped the `while (` count from 9 to 3, and
  removed the Mistral `content as string` assertion. The only remaining
  text-completion `iterator.next` match is the `toAsyncGenerator`
  compatibility adapter that exposes Effect streams through the public
  `AsyncGenerator<LlmChunk>` provider contract.
- The request-response queue stream slice replaced the Effectful
  `waitForResponse` generator loop with `Stream.fromQueue`,
  `Stream.filterMapEffect`, `Result`, and `Stream.runHead`, dropping the
  remaining `while (` count from 3 to 2. The two remaining production `while`
  hits are synchronous parsing/CLI traversal loops, not async polling loops.
- The gateway RPC WebSocket cause-handling slice removed the Promise `.catch`
  around the socket program by sandboxing the Effect and handling the resulting
  `Cause` in the Effect pipeline before the Fastify fire-and-forget
  `runPromise` boundary.
- The client RPC acquisition cause tap slice removed the Promise `.catch` used
  only to update connection state on runtime/client acquisition failure.
  `effect-rpc-client.ts` now uses `Effect.tapCause` and `Cause.pretty` before
  the public Promise boundary.
- `Record<string, any>` and `throwLibrarianServiceError` are now clean in
  `ts/packages`.

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
  - Resolved by the typed runtime loop and ref-backed state slices below.
- Verification:
  - `bun run --cwd ts/packages/base build`
  - `bun run --cwd ts/packages/flow build`
  - `bun run --cwd ts/packages/flow test -- src/__tests__/librarian-service.test.ts`
  - `bun run --cwd ts/packages/flow test`
  - `cd ts && bun run check`
  - `cd ts && bun run build`
  - `cd ts && bun run test`
  - `git diff --check`

### 2026-06-02: Librarian Tagged Operation Helper Slice

- Status: migrated and root-verified.
- Completed:
  - Removed the librarian `throwLibrarianServiceError` helper.
  - `get-document-metadata`, `list-children`, `upload-chunk`,
    `get-upload-status`, and `abort-upload` now dispatch through local
    Effect-returning helpers that fail with `LibrarianServiceError`.
  - Compatibility methods for those operations now return Promise facades
    backed by `Effect.runPromise`.
  - The librarian tests now await the Promise compatibility facade for upload
    status.
- Remaining:
  - Resolved by the typed runtime loop and ref-backed state slices below.
- Verification:
  - `bun run --cwd ts/packages/flow test -- src/__tests__/librarian-service.test.ts`
  - `bun run --cwd ts/packages/flow build`
  - `cd ts && bun run check`
  - `bun run --cwd ts/packages/flow test`
  - `cd ts && bun run build`
  - `cd ts && bun run test`
  - `git diff --check`

### 2026-06-02: Librarian Typed Runtime Loop Slice

- Status: migrated and root-verified.
- Completed:
  - `ts/packages/flow/src/librarian/service.ts` now exposes a typed
    `LibrarianService` interface instead of `AsyncProcessorRuntime &
    Record<string, any>`.
  - Service construction now uses `makeAsyncProcessor<LibrarianServiceError>`
    with `runEffect`; the old method-bag `run` override and
    `as LibrarianService` cast are gone.
  - The librarian startup poller now uses `Effect.whileLoop`.
  - The local operation helpers retrieve the initialized service through an
    Effect gate rather than closing over an unsafe partially built value.
- Remaining:
  - Resolved by the ref-backed state slice below.
- Verification:
  - `bun run --cwd ts/packages/flow build`
  - `cd ts && bun run check`
  - `bun run --cwd ts/packages/flow test`
  - `cd ts && bun run build`
  - `cd ts && bun run test`
  - `git diff --check`

### 2026-06-02: Librarian Ref-Backed State Slice

- Status: migrated and root-verified.
- Completed:
  - `ts/packages/flow/src/librarian/service.ts` now stores documents,
    processing records, upload sessions, collection manager, and pubsub
    handles in `SynchronizedRef<LibrarianServiceState>`.
  - Document, processing, upload, collection, persistence, load, and stop paths
    now read snapshots or mutate cloned maps/managers through the ref instead
    of writing fields on the service object.
  - Upload chunk updates clone nested `UploadSession.chunks` before replacing
    the upload map entry, avoiding mutable nested state hidden behind the ref.
  - Librarian response producers and consumers are read/nullified through
    ref-backed handles.
- Verification:
  - `bun run --cwd ts/packages/flow build`
  - `bun run --cwd ts/packages/flow test -- src/__tests__/librarian-service.test.ts`
  - `cd ts && bun run check`
  - `bun run --cwd ts/packages/flow test`
  - `cd ts && bun run build`
  - `cd ts && bun run test`
  - `git diff --check`

### 2026-06-02: Client RPC Managed Runtime Slice

- Status: migrated and root-verified.
- Completed:
  - `ts/packages/client/src/socket/effect-rpc-client.ts` now builds one
    `ManagedRuntime` from the RPC client layer instead of manually creating a
    `Scope`, building the layer, and calling `Effect.runPromise` for every
    operation.
  - RPC dispatch and stream dispatch continue to expose the existing
    Promise-returning `EffectRpcClient` facade, but they run through the managed
    runtime and close with `runtime.dispose()`.
  - The Effect RPC socket path now consumes `Socket.layerWebSocketConstructorGlobal`
    instead of a duplicate local WebSocket constructor layer.
  - Dispatch payload construction now uses `DispatchPayload.make(...)` so
    schema classes are not instantiated with `new`.
  - Client socket logging and timestamp creation now use Effect `Logger` and
    `Clock` instead of direct console and `Date.now()` calls in the touched
    surface.
- Verification:
  - `bun run --cwd ts/packages/client build`
  - `cd ts && bun run check`
  - `bun run --cwd ts/packages/client test`
  - `cd ts && bun run build`
  - `cd ts && bun run test`
  - `git diff --check`

### 2026-06-02: Client WebSocket Adapter Error Slice

- Status: migrated and root-verified.
- Completed:
  - `ts/packages/client/src/socket/websocket-adapter.ts` now models host
    fallback failures with `WebSocketAdapterError` via
    `S.TaggedErrorClass`.
  - Synchronous `getWebSocketConstructor()` and `getRandomValues()` facades
    keep their public signatures while using `Result.try` instead of local
    `try`/`catch` blocks.
  - Runtime predicates now narrow WebSocket constructor modules and crypto
    modules without the previous constructor/result type assertions.
  - New adapter tests cover global WebSocket selection, optional `ws`
    fallback, global crypto, typed crypto failure, and typed adapter errors.
- Verification:
  - `bun run --cwd ts/packages/client build`
  - `bun run --cwd ts/packages/client test -- src/__tests__/websocket-adapter.test.ts`
  - `bun run --cwd ts/packages/client test`
  - `cd ts && bun run check`
  - `cd ts && bun run build`
  - `cd ts && bun run test`
  - `git diff --check`
  - `git diff --check`

### 2026-06-02: Client Socket Tagged Error And JSON Slice

- Status: migrated and root-verified.
- Completed:
  - `ts/packages/client/src/socket/trustgraph-socket.ts` now models socket API
    failures with `TrustGraphSocketError` via `S.TaggedErrorClass`.
  - Flow/blueprint JSON response parsing now uses Schema decoding through
    `S.UnknownFromJsonString` instead of raw `JSON.parse`.
  - Token-cost config JSON keeps the previous invalid-string fallback behavior
    while decoding through Schema/Option.
  - Connection-state listener isolation now uses `Result.try` and typed socket
    errors instead of a local `try`/`catch`.
  - Flow start, row embeddings, collection update, and response-error
    failures now reject with tagged socket errors instead of normal `Error`.
  - Flow API tests cover invalid JSON and response-error rejections.
- Verification:
  - `bun run --cwd ts/packages/client build`
  - `bun run --cwd ts/packages/client test -- src/__tests__/flows-api.test.ts`
  - `cd ts && bun run check`
  - `bun run --cwd ts/packages/client test`
  - `cd ts && bun run build`
  - `cd ts && bun run test`
  - `git diff --check`

### 2026-06-02: Client Newable Factory Compatibility Decision

- Status: documented no-op for the current loop.
- Evidence:
  - `ts/packages/workbench/src/atoms/workbench.ts` constructs
    `new BaseApi(...)`.
  - `ts/packages/client/src/__tests__/flows-api.test.ts` constructs
    `new FlowsApi(...)`, and sibling API facades expose the same constructor
    shape.
  - `EffectRpcClient` and `BaseApi` also preserve callable factory exports for
    compatibility with the vendored TrustGraph client shape.
- Decision:
  - The remaining `newableFactory(... ) as unknown as NewableFactory<...>`
    assertions in client socket files are TypeScript compatibility boundaries,
    not Effect error/requirement channel assertions and not replacements for an
    Effect primitive.
  - Removing them safely requires a deliberate public API redesign or explicit
    class implementations for every API facade, not a local Effect-native
    rewrite.
- Verification:
  - Current client/root verification from the tagged error slice covers this
    no-op decision.

### 2026-06-02: Service Entrypoint Runtime Slice

- Status: migrated and root-verified.
- Completed:
  - Remaining flow service `run(): Promise<void>` program facades now use
    `ManagedRuntime.make(Layer.empty)` instead of direct
    `Effect.runPromise(program)`.
  - Remaining flow service modules now expose `runMain()` through
    `NodeRuntime.runMain(program)`.
  - Local `ts/scripts/run-*` launchers for gateway, prompt, chunker,
    extractor, PDF decoder, embeddings, triples, graph/document embeddings,
    text-completion providers, and MCP tool service now delegate directly to
    `runMain()`.
  - Direct `Effect.runPromise(program)` matches in `ts/packages/flow/src` are
    clean. Remaining `Effect.runPromise` matches are callback/Promise
    compatibility boundaries for later slices.
- Verification:
  - `bun run --cwd ts/packages/flow build`
  - `git diff --check`
  - `cd ts && bun run check`
  - `bun run --cwd ts/packages/flow test`
  - `cd ts && bun run build`
  - `cd ts && bun run test`

### 2026-06-02: Base Processor Compatibility Runtime Slice

- Status: migrated and root-verified.
- Completed:
  - `ts/packages/base/src/processor/async-processor.ts` now uses a
    `ManagedRuntime` for Promise compatibility methods, signal-shutdown
    execution, and legacy `AsyncProcessor.launch`.
  - `ts/packages/base/src/processor/flow.ts` now owns a per-flow
    `ManagedRuntime` for `start`, `stop`, `runInCompatibilityScope`, and
    Promise resource facades.
  - `ts/packages/base/src/processor/flow-processor.ts` now uses a
    `ManagedRuntime` for the public `start(context)` facade instead of a local
    `Effect.runPromiseWith` runner.
  - `ts/packages/base/src/spec/parameter-spec.ts` now routes legacy `add`
    through `flow.runInCompatibilityScope(...)`, matching the other specs.
  - Subagent checks confirmed `NodeRuntime` is process-entrypoint-only here;
    `@trustgraph/base` should not add an `@effect/platform-node` dependency
    for these compatibility facades.
- Remaining:
  - Constructor `as unknown as` shims in base processors preserve
    callable-plus-newable public exports and are compatibility boundaries for
    this loop.
  - Typed string lookup casts in `Flow` need a real typed-spec/key redesign;
    `HashMap`/`MutableHashMap` alone cannot infer `T` from a bare string.
- Verification:
  - `bun run --cwd ts/packages/base build`
  - `bun run --cwd ts/packages/base test`
  - `cd ts && bun run check`
  - `git diff --check`
  - `cd ts && bun run build`
  - `cd ts && bun run test`

### 2026-06-02: Base Flow Definition Schema Slice

- Status: migrated and root-verified.
- Completed:
  - `ts/packages/base/src/processor/flow-processor.ts` now validates
    `config.flows` with Effect Schema instead of local
    `Predicate`/object/string-record guards.
  - Invalid flow definition payloads still log/skip and preserve the existing
    config-handler and acknowledgement behavior.
  - `ts/packages/base/src/__tests__/flow-processor-runtime.test.ts` now covers
    an invalid nested flow definition that is acknowledged without starting
    resources.
- Verification:
  - `bun run --cwd ts/packages/base test -- src/__tests__/flow-processor-runtime.test.ts`
  - `bun run --cwd ts/packages/base build`
  - `cd ts && bun run check`
  - `cd ts && bun run build`
  - `cd ts && bun run test`
  - `git diff --check`

### 2026-06-02: Text Completion Stream Sentinel Slice

- Status: migrated and root-verified.
- Completed:
  - `ts/packages/flow/src/model/text-completion/{ollama,openai,mistral,azure-openai,claude,openai-compatible}.ts`
    now return the `Stream.unfold` end sentinel with
    `Effect.as(Effect.void, undefined)`.
  - Removed six `Effect.void as Effect.Effect<undefined>` assertions without
    replacing them with `Effect.succeed(undefined)`, which `@effect/tsgo`
    flags as a diagnostic.
- Verification:
  - `bun run --cwd ts/packages/flow build`
  - `cd ts && bun run check`
  - `bun run --cwd ts/packages/flow test`
  - `cd ts && bun run build`
  - `cd ts && bun run test`
  - `git diff --check`

### 2026-06-02: Text Completion Generator Boundary Slice

- Status: migrated and root-verified.
- Completed:
  - `ts/packages/flow/src/model/text-completion/common.ts` now rejects
    fallback `AsyncGenerator.throw(...)` calls with the mapped tagged provider
    error directly instead of running `Effect.fail(...)` through
    `Effect.runPromise`.
  - The custom generator object no longer uses `as AsyncGenerator`,
    `as Promise<IteratorResult<LlmChunk>>`, or `as LlmChunk` assertions.
  - Added a focused unit test for fallback throw mapping.
- Verification:
  - `bun run --cwd ts/packages/flow test -- src/__tests__/text-completion-common.test.ts`
  - `bun run --cwd ts/packages/flow build`
  - `cd ts && bun run check`
  - `bun run --cwd ts/packages/flow test`
  - `cd ts && bun run build`
  - `cd ts && bun run test`
  - `git diff --check`

### 2026-06-02: Text Completion Provider Status Narrowing Slice

- Status: migrated and root-verified.
- Completed:
  - `ts/packages/flow/src/model/text-completion/common.ts` now uses
    `effect/Predicate` narrowing for provider `status` / `statusCode`
    inspection instead of local record assertions.
  - `ts/packages/flow/src/__tests__/text-completion-common.test.ts` covers
    both rate-limit status fields.
- Verification:
  - `bun run --cwd ts/packages/flow test -- src/__tests__/text-completion-common.test.ts`
  - `bun run --cwd ts/packages/flow build`
  - `cd ts && bun run check`
  - `bun run --cwd ts/packages/flow test`
  - `cd ts && bun run build`
  - `cd ts && bun run test`
  - `git diff --check`

### 2026-06-02: Base Parameter Spec Accessor Slice

- Status: migrated and root-verified.
- Completed:
  - `ts/packages/base/src/spec/parameter-spec.ts` now models
    `ParameterSpec<T>` with an Effect Schema codec. Legacy parameter specs
    default to `S.Unknown`, preserving name-based registration while making
    typed access schema-backed.
  - `ts/packages/base/src/processor/flow.ts` now exposes
    `flow.parameterEffect(spec)` and `flow.parameter(spec)` for inferred,
    Schema-decoded parameter values. String lookup remains available as an
    `unknown` compatibility escape instead of a caller-chosen generic type.
  - Parameter schema failures now fail with the tagged
    `FlowParameterDecodeError` rather than a normal `Error`.
  - `ts/packages/flow/src/chunking/service.ts` now declares numeric chunk
    parameters once and retrieves them through the typed spec-object accessor.
  - `ts/packages/base/src/__tests__/flow-spec-runtime.test.ts` covers typed
    parameter decoding, legacy string lookup, missing parameter errors, sync
    accessor decoding, and schema mismatch errors.
- Remaining:
  - Add typed spec-object accessors for producers and requestors so call sites
    can stop spelling generic string lookups for those registries too.
- Verification:
  - `bun run --cwd ts/packages/base test -- src/__tests__/flow-spec-runtime.test.ts`
  - `bun run --cwd ts/packages/base build`
  - `bun run --cwd ts/packages/flow build`
  - `cd ts && bun run check`
  - `bun run --cwd ts/packages/base test`
  - `bun run --cwd ts/packages/flow test`
  - `cd ts && bun run build`
  - `cd ts && bun run test`
  - `git diff --check`

### 2026-06-02: Base Producer And Requestor Spec Accessor Slice

- Status: migrated and root-verified.
- Completed:
  - `ts/packages/base/src/spec/producer-spec.ts` now exposes
    `ProducerSpec<T>.producerEffect(flow)` and stores typed producer handles in
    a per-spec WeakMap keyed by `Flow`.
  - `ts/packages/base/src/spec/request-response-spec.ts` now exposes
    `RequestResponseSpec<TReq, TRes>.requestorEffect(flow)` and stores typed
    requestor handles in a per-spec WeakMap keyed by `Flow`.
  - Spec finalizers remove only the exact handle they registered, avoiding
    stale finalizers deleting newer registrations for the same flow/spec pair.
  - `ts/packages/base/src/processor/flow.ts` now supports
    `flow.producerEffect(spec)`, `flow.requestorEffect(spec)`,
    `flow.producer(spec)`, and `flow.requestor(spec)` while keeping string
    accessors as untyped compatibility escapes.
  - Base service adapters and flow service handlers now reuse the same hoisted
    producer/requestor spec object in their spec arrays and handler lookups.
  - `ts/packages/base/src/__tests__/flow-spec-runtime.test.ts` covers typed
    spec-object lookups, duplicate spec identity failures, and scoped
    finalizer cleanup for producer and requestor handles.
- Remaining:
  - Bare string `Flow` producer/requestor accessors remain compatibility
    escapes for external/legacy callers, but new Effect service code should use
    spec objects.
- Verification:
  - `bun run --cwd ts/packages/base test -- src/__tests__/flow-spec-runtime.test.ts`
  - `bun run --cwd ts/packages/base build`
  - `bun run --cwd ts/packages/flow build`
  - `bun run --cwd ts/packages/base test`
  - `bun run --cwd ts/packages/flow test`
  - `cd ts && bun run check`
  - `cd ts && bun run build`
  - `cd ts && bun run test`
  - `git diff --check`

### 2026-06-02: Native PubSub Boundary Slice

- Status: migrated and package-verified.
- Completed:
  - Confirmed Effect's native `PubSub` module is an in-process asynchronous hub
    with scoped subscriptions, not a NATS/Pulsar-compatible broker boundary.
  - Kept TrustGraph's `PubSubBackend` and `PubSub` service as the broker
    adapter layer because it owns topics, broker producers/consumers,
    acknowledgement, schema codecs, and backend lifecycle.
  - Removed the unused legacy `ts/packages/base/src/messaging/subscriber.ts`
    implementation, which duplicated in-process async queue/fanout behavior.
  - Removed the corresponding `makeAsyncQueue`, `makeSubscriber`,
    `Subscriber`, and `AsyncQueue` barrel exports from
    `ts/packages/base/src/messaging/index.ts`.
- Remaining:
  - Future in-process fanout or request-streaming code should use
    `effect/PubSub`, `Queue`, `Stream.fromPubSub`, or `Channel.fromPubSub`
    rather than adding another local async queue implementation.
  - Do not replace `PubSubBackend` with `effect/PubSub` unless the code path is
    explicitly local-only and does not need broker semantics.
- Verification:
  - `bun run --cwd ts/packages/base build`
  - `bun run --cwd ts/packages/base test`
  - `cd ts && bun run check`

### 2026-06-02: Gateway Streaming Callback Slice

- Status: migrated and root-verified.
- Completed:
  - `ts/packages/flow/src/gateway/dispatch/manager.ts` now exposes
    `dispatchGlobalServiceStreamingEffect` and
    `dispatchFlowServiceStreamingEffect` so Effect callers can handle stream
    chunks without Promise callback re-entry.
  - The existing Promise-returning streaming methods remain as compatibility
    facades and wrap responders with `Effect.tryPromise`.
  - `ts/packages/flow/src/gateway/rpc-server.ts` now writes stream chunks into
    the RPC queue through the dispatcher Effect path, removing the prior
    `Effect.context` plus `Effect.runPromiseWith(context)` bridge.
  - `ts/packages/client/src/socket/effect-rpc-client.ts` now uses
    `Stream.runForEachWhile` for early stream termination instead of throwing a
    synthetic `StopStreaming` tagged error.
  - Gateway dispatcher tests now exercise both the Promise compatibility
    streaming path and the Effect-native responder path.
- Remaining:
  - `ts/packages/flow/src/gateway/rpc-protocol.ts` remains a Fastify socket
    compatibility bridge, not a direct replacement target for Effect RPC
    server layers yet.
- Verification:
  - `bun run --cwd ts/packages/flow build`
  - `bun run --cwd ts/packages/client build`
  - `bunx --bun vitest run src/__tests__/gateway-dispatcher.test.ts`
  - `bunx --bun vitest run src/__tests__/rpc-timeout.test.ts`
  - `cd ts && bun run check`
  - `cd ts && bun run build`
  - `cd ts && bun run test`
  - `git diff --check`

### 2026-06-02: Client Streaming Facade Normalization Slice

- Status: migrated and root-verified.
- Completed:
  - `ts/packages/client/src/socket/trustgraph-socket.ts` now decodes the
    legacy streaming envelope with Schema before service-specific callback
    handling.
  - Streaming payload reads now use `effect/Predicate` property narrowing
    helpers instead of repeated response-wrapper assertions.
  - Graph RAG, document RAG, text completion, prompt, agent, and document
    stream callbacks now use a shared `streamComplete(...)` helper. The RPC
    `DispatchStreamChunk.complete` bit is the default transport completion
    source, with legacy service markers preserved for public compatibility.
  - Explainability triples are decoded through a recursive Schema instead of
    `as Triple[]`.
  - The focused client test now proves normalized `DispatchStreamChunk`
    completion flows through `graphRagStreaming` and final metadata.
- Verification:
  - `bunx --bun vitest run src/__tests__/rpc-timeout.test.ts`
  - `bun run --cwd ts/packages/client build`
  - `cd ts && bun run check:tsgo`
  - `bun run --cwd ts/packages/client test`
  - `cd ts && bun run check`
  - `cd ts && bun run build`
  - `cd ts && bun run test`
  - `git diff --check`

### 2026-06-02: Ollama Embeddings Effectful Layer Slice

- Status: migrated and root-verified.
- Completed:
  - `ts/packages/flow/src/embeddings/ollama.ts` now exposes
    `makeOllamaEmbeddingsEffect` for effectful config loading and service
    construction.
  - `OllamaEmbeddingsLive` now uses `Layer.effect` and maps config/load
    failures into `EmbeddingsError` instead of preconstructing the service with
    `Layer.succeed`.
  - The direct `makeOllamaEmbeddings(config)` factory remains as a
    compatibility facade, while the canonical `program` entrypoint preserves
    the provider tagged error channel.
  - Ollama response JSON parsing no longer uses a Promise type assertion.
  - The focused embeddings tests now cover both direct factory use and the
    effectful `OllamaEmbeddingsLive` layer.
- Verification:
  - `bunx --bun vitest run src/__tests__/ollama-embeddings.test.ts`
  - `bun run --cwd ts/packages/flow build`
  - `cd ts && bun run check:tsgo`
  - `bun run --cwd ts/packages/flow test`
  - `cd ts && bun run check`
  - `cd ts && bun run build`
  - `cd ts && bun run test`

### 2026-06-02: FalkorDB Scoped Client Lifecycle Slice

- Status: migrated and root-verified.
- Completed:
  - `ts/packages/flow/src/storage/triples/falkordb.ts` and
    `ts/packages/flow/src/query/triples/falkordb.ts` now model FalkorDB client
    acquisition with `Effect.acquireRelease`.
  - FalkorDB Live layers now use `Layer.effect` and own Redis client
    disconnect finalizers through the layer scope.
  - Direct Promise compatibility factories and direct service factories now
    bracket each operation with scoped acquisition instead of hiding mutable
    `Effect.cached` connection slots.
  - Legacy `makeTriplesStoreService` and `makeTriplesQueryService` provider
    hooks now acquire scoped FalkorDB services and map acquisition failures to
    `ProcessorLifecycleError`; modern `program` entrypoints preserve the
    FalkorDB tagged layer error type.
  - FalkorDB query row field extraction now uses `effect/Predicate` narrowing
    instead of record/string type assertions.
  - New lifecycle tests use fake clients/graphs to prove connect on acquire
    and disconnect on scope close for both triples store and triples query.
- Verification:
  - `bunx --bun vitest run src/__tests__/falkordb-lifecycle.test.ts`
  - `bun run --cwd ts/packages/flow build`
  - `cd ts && bun run check`
  - `bun run --cwd ts/packages/flow test`
  - `cd ts && bun run build`
  - `cd ts && bun run test`
  - `git diff --check`

### 2026-06-02: Qdrant Config, Schema, And Fakeable Construction Slice

- Status: migrated and root-verified.
- Completed:
  - Added `ts/packages/flow/src/qdrant/client.ts` as the narrow fakeable
    Qdrant surface used by graph/doc embedding store/query modules.
  - Graph and document Qdrant store/query constructors now create clients
    through `Effect.try`, load Qdrant config in Effect, and map config/client
    failures into their existing `S.TaggedErrorClass` errors.
  - Graph and document query payload extraction now uses
    `Schema.decodeUnknownEffect(...).pipe(Effect.option)` and skips malformed
    Qdrant payloads without type assertions.
  - Qdrant graph/doc query Live layers and graph store Live layer now use
    `Layer.effect` instead of preconstructing services with `Layer.succeed`.
  - Legacy graph store/query/doc query processor providers now acquire Qdrant
    services with named `Effect.fn` providers and map startup failures to
    `ProcessorLifecycleError`.
  - The installed Qdrant client still has no public close/disconnect method,
    so no `Effect.acquireRelease` finalizer was added for Qdrant.
- Verification:
  - `bunx --bun vitest run src/__tests__/qdrant-embeddings.test.ts`
  - `bun run --cwd ts/packages/flow build`
  - `cd ts && bun run check:tsgo`
  - `bun run --cwd ts/packages/flow test`
  - `cd ts && bun run check`
  - `cd ts && bun run build`
  - `cd ts && bun run test`
  - `git diff --check`

### 2026-06-02: Text Completion Provider Stream Helper Slice

- Status: migrated and root-verified.
- Completed:
  - `ts/packages/flow/src/model/text-completion/common.ts` now exposes
    `streamTextCompletionChunks`, an Effect-native helper built on
    `Stream.fromAsyncIterable`, `Ref`, `Stream.filterMap`/`Result`, and a final
    token chunk append.
  - OpenAI, Azure OpenAI, OpenAI-compatible, Mistral, Ollama, and Claude
    streaming providers now share the helper instead of each hand-rolling
    `Stream.unfold` plus `iterator.next` loops.
  - Mistral non-streaming and streaming content normalization now uses
    `effect/Predicate` and `Option` narrowing through `textFromContent`, removing
    the prior `content as string` assertion.
  - The helper uses the installed Effect beta's `Option.fromNullishOr` and
    Result-shaped `Stream.filterMap` API, verified by `check:tsgo`.
  - `ts/packages/flow/src/__tests__/text-completion-common.test.ts` covers
    token accumulation/final chunk emission and non-string content narrowing.
- Remaining:
  - Full Effect AI provider swaps still need parity tests first; current OpenAI
    and Azure behavior is Chat Completions based, no installed
    Azure/Mistral/Ollama Effect AI provider exists, and Anthropic needs explicit
    text/token/streaming/rate-limit parity coverage before replacement.
- Verification:
  - `bunx --bun vitest run src/__tests__/text-completion-common.test.ts`
  - `cd ts && bun run check:tsgo`
  - `bun run --cwd ts/packages/flow build`
  - `bun run --cwd ts/packages/flow test`
  - `cd ts && bun run check`
  - `cd ts && bun run build`
  - `cd ts && bun run test`
  - `git diff --check`

### 2026-06-02: Request-Response Queue Stream Slice

- Status: migrated and root-verified.
- Completed:
  - `ts/packages/base/src/messaging/runtime.ts` now waits for accepted
    request-response replies by converting the response `Queue` to a
    `Stream.fromQueue`.
  - Recipient filtering now uses `Stream.filterMapEffect` with `Result` to skip
    partial responses until the recipient returns `true`.
  - `Stream.runHead` replaces the prior `while (true)`/`Queue.take` loop and
    preserves the existing timeout behavior around request-response calls.
  - `ts/packages/base/src/__tests__/messaging-runtime.test.ts` now covers
    recipient filtering across partial and final responses.
- Remaining:
  - The two remaining production `while (` matches are `agent/react/parser.ts`
    line-buffer parsing and `cli/src/commands/util.ts` Commander parent
    traversal; neither is async polling or resource ownership.
- Verification:
  - `bunx --bun vitest run src/__tests__/messaging-runtime.test.ts`
  - `bun run --cwd ts/packages/base build`
  - `bun run --cwd ts/packages/base test`
  - `cd ts && bun run check`
  - `cd ts && bun run build`
  - `cd ts && bun run test`
  - `git diff --check`

### 2026-06-02: Gateway RPC WebSocket Cause Handling Slice

- Status: migrated and root-verified.
- Completed:
  - `ts/packages/flow/src/gateway/server.ts` now handles RPC WebSocket program
    defects and interruptions inside the Effect pipeline with `Effect.sandbox`,
    `Effect.catch`, and `Cause.pretty`.
  - The previous Promise `.catch(...)` around `Effect.runPromise(...)`, plus the
    nested `Effect.runPromise` used only for logging and socket close, is removed.
  - The outer `Effect.runPromise` remains as the Fastify WebSocket host boundary.
- Verification:
  - `cd ts && bun run check:tsgo`
  - `bun run --cwd ts/packages/flow build`
  - `bun run --cwd ts/packages/flow test`
  - `cd ts && bun run check`
  - `cd ts && bun run build`
  - `cd ts && bun run test`
  - `git diff --check`

### 2026-06-02: Client RPC Acquisition Cause Tap Slice

- Status: migrated and root-verified.
- Completed:
  - `ts/packages/client/src/socket/effect-rpc-client.ts` now observes
    runtime/client acquisition failures with `Effect.tapCause` and
    `Cause.pretty`.
  - Removed the Promise `.catch(...)` that only updated local connection state
    after `runtime.runPromise(TrustGraphRpcClientService)`.
  - Removed the local `errorMessage` helper and its message-field assertion.
  - Public `dispatch`, `dispatchStream`, and `close` Promise facades remain
    compatibility boundaries.
- Verification:
  - `cd ts && bun run check:tsgo`
  - `bun run --cwd ts/packages/client build`
  - `bun run --cwd ts/packages/client test`
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
  - Config service, KnowledgeCore service, FlowManager, and Librarian
    ref-backed state slices are complete. Follow-up service work should focus
    on scoped layers, schedules where polling semantics allow, and managed
    persistence providers rather than direct mutable service fields.
  - Flow service startup facades now consistently use `ManagedRuntime`, and
    local scripts should delegate to `runMain()` instead of adding local
    `.catch(console.error/process.exit)` wrappers.
  - Persistence IO should move toward `FileSystem` or `KeyValueStore` where
    the installed beta has the needed provider surface.
- Base messaging/processors:
  - Processor/flow Promise compatibility now uses `ManagedRuntime`; keep
    `NodeRuntime` only for process `runMain()` entrypoints.
  - Subscriber queues/maps and dynamic flow state should continue moving
    toward `Queue`, `Deferred`, `SynchronizedRef`, `Schedule`, and scoped
    layers.
  - The legacy `messaging/subscriber.ts` async queue/fanout implementation is
    removed. Use native `effect/PubSub` for future in-process fanout, while
    keeping `PubSubBackend` for broker-backed messaging.
  - Existing constructor shims preserve callable-plus-newable public exports;
    removing them needs a public API split or real class redesign.
  - Typed string registries in `Flow` now have Schema-backed parameter specs
    and typed producer/requestor spec-object accessors. New service handlers
    should hoist spec objects and use those accessors; bare string accessors
    remain compatibility escapes.
- Gateway/client:
  - `EffectRpcClient` now owns its socket/RPC layer with `ManagedRuntime`.
    Socket errors/JSON parsing now use tagged errors and Schema decoding.
    The remaining client `newableFactory` assertions are documented as public
    API compatibility boundaries for this loop.
  - Gateway `DispatchStream` now uses Effect-native dispatcher streaming
    callbacks instead of nested `Effect.runPromiseWith`, and client streaming
    facade callbacks now decode the legacy envelope through Schema before
    applying service-specific public callback semantics.
  - Do not make `gateway/rpc-protocol.ts` the next cleanup target: it is a
    Fastify socket compatibility bridge while the public Effect RPC server
    layers require SocketServer or Effect HTTP routing.
  - WebSocket adapter host fallbacks now use `Result.try` and tagged adapter
    errors while preserving sync exports.
- RAG/providers/storage:
  - RAG and agent requestor bridges are complete: `toPromiseRequestor` has no
    remaining `ts/packages` matches.
  - Provider SDKs and storage clients should become managed resources where
    they have meaningful lifecycle.
  - Ollama embeddings now has an effectful canonical layer. There is no
    installed Effect AI Ollama provider package, so future Ollama work should
    focus on local Effect wrappers/adapters rather than provider replacement.
  - Full text-completion provider swaps need parity tests first. OpenAI and
    Azure currently use Chat Completions while `@effect/ai-openai` is Responses
    API oriented, and no installed Azure/Mistral/Ollama Effect AI provider is
    available. Anthropic is the closest direct provider swap, but must preserve
    text, token counts, streaming final usage, and rate-limit mapping.
  - FalkorDB scoped lifecycle is complete for triples query/store. Use the
    fakeable client/graph factory pattern from that slice for future storage
    client tests.
  - Qdrant config/schema/fakeability is complete for graph/doc embedding
    store/query modules. Qdrant still has no close/disconnect surface in the
    installed client, so do not reopen it as an `acquireRelease` close slice
    without new SDK evidence.
  - Shared text-completion stream iteration and the Mistral content assertion are
    complete. The remaining provider-layer item is parity-backed Effect AI
    adapter work, not a direct SDK swap.

## Ranked Findings

### P2: Provider Layer And Effect AI Cleanup

- TrustGraph evidence:
  - `ts/packages/flow/src/model/text-completion/*.ts`
- Effect primitives:
  - `Config`, `ConfigProvider`, `Metric`, `Logger`,
    `effect/unstable/ai/LanguageModel`, `effect/unstable/ai/EmbeddingModel`,
    Effect AI OpenAI/Anthropic provider layers.
- Rewrite shape:
  - Add an Effect AI adapter layer beside the current `LlmProvider` contract
    before flipping any public provider interface.
  - Use Effect AI provider layers only where parity is proven.
  - Keep OpenAI-compatible/Azure-compatible behavior behind parity tests
    because current code uses chat-completions style APIs while the Effect
    OpenAI language model is Responses API backed.
- Tests:
  - Provider parity for `LlmResult`, final streaming chunk token counts, 429
    mapping, missing-token config failures, and OpenAI-compatible local-server
    behavior.

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

1. Provider layer and Effect AI cleanup.
2. MCP parity/deletion decision and workbench platform polish.

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
- Plain synchronous loops for parsing or tree traversal are not Effect migration
  blockers unless they hide async polling, resource ownership, or callback
  scheduling.
- JSON stringification in tests or wire-contract fixtures. Production JSON
  encode/decode should prefer schema codecs when the encoded form can be
  preserved.
- Client `newableFactory` assertions that preserve vendored callable-plus-new
  API facades are compatibility boundaries unless the public constructor API is
  intentionally redesigned.
- Base `AsyncProcessor`, `Flow`, and `FlowProcessor` callable-plus-newable
  export assertions are compatibility boundaries unless the public constructor
  API is intentionally redesigned.
- TrustGraph `PubSubBackend` / backend `PubSub` service is a broker adapter
  boundary for NATS/Pulsar-style topics, acknowledgement, schema codecs, and
  backend lifecycle. Effect's native `PubSub` can replace in-process fanout
  helpers, but not the distributed broker abstraction by itself.
- `ts/packages/flow/src/gateway/rpc-protocol.ts` is a Fastify socket
  compatibility bridge. Do not flag its internal connection maps/sets as a
  standalone replacement target until the gateway is ready to move onto Effect
  SocketServer or Effect HTTP routing.

## Acceptance For Final Loop Completion

The overall playbook loop is complete only when:

- All remaining playbook signal matches are migrated or documented as no-op
  external-boundary cases with concrete evidence.
- No P0/P1/P2 migration item remains in this audit.
- `cd ts && bun run check`, `cd ts && bun run build`, `cd ts && bun run test`,
  and `git diff --check` pass after the final migration slice.
