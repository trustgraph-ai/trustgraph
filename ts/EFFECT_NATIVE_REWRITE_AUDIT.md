# TrustGraph Effect-Native Rewrite Opportunity Audit

This is the current backlog snapshot for the playbook in
`ts/EFFECT_NATIVE_REWRITE_PLAYBOOK.md`. The branch is `ts-port-effect-v4`.
The unrelated local file `.idea/effect.intellij.xml` must stay uncommitted.

## Inputs

Verified source roots:

- TrustGraph TS port: `/home/elpresidank/YeeBois/dev/trustgraph/ts`
- Effect v4 subtree: `/home/elpresidank/YeeBois/projects/beep-effect2/.repos/effect-v4`
- Installed Effect beta used by this workspace: `ts/node_modules/effect`

Current signal counts from `ts/packages` after the 2026-06-02 Effect AI
adapter and native request/response PubSub slices:

| Signal | Count |
| --- | ---: |
| `Effect.runPromise` | 169 |
| `Effect.runPromiseWith` | 0 |
| `Effect.cached` | 0 |
| `Layer.succeed` | 12 |
| `Map<` | 37 |
| `WebSocket` | 72 |
| `new Map` | 59 |
| `toPromiseRequestor` | 0 |
| `makeAsyncProcessor` | 19 |
| `receive(` | 17 |
| `while (` | 2 |
| `new Error` | 7 |
| `new Promise` | 9 |
| `JSON.parse` | 4 |
| `localStorage` | 11 |
| `JSON.stringify` | 8 |
| `setTimeout` | 3 |
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
- The base producer scoped runtime slice moved the legacy `makeProducer`
  Promise facade onto the existing `makeEffectProducerFromPubSub` scoped
  factory. Public `start`/`send`/`stop` remain Promise compatibility
  boundaries, while producer allocation, flush, and finalizer close now go
  through the Effect runtime path.
- The NATS typed boundary slice removed the dynamic `import("nats")` header
  path and maps header construction plus `ack()`/`nak()` failures into tagged
  `PubSubError`s with `Effect.try`. The `receive(` and `JSON.stringify` count
  increases are from the new mocked NATS backend test, not production code.
- The NATS selective 404 slice replaced catch-all stream/consumer create
  fallbacks with an internal `S.TaggedErrorClass` lookup wrapper plus
  `Effect.catchIf` recovery only for NATS JetStream missing-resource errors.
  Non-missing lookup failures now stay on the typed failure path without
  attempting to create streams or durable consumers.
- The consumer rate-limit retry slice wired the previously unused
  `rateLimitTimeoutMs` option and `TG_RATE_LIMIT_TIMEOUT_MS` config into both
  legacy and Effect-native consumers. Repeated `TooManyRequestsError` failures
  now retry with `Schedule.spaced` until success or a tagged rate-limit timeout.
  The `new Error` count dropped by one because a touched consumer test fixture
  no longer uses a normal `Error`.
- The consumer concurrency ownership slice changed the Effect-native consumer
  runtime so `concurrency > 1` allocates one backend consumer per worker instead
  of sharing a single `BackendConsumer.receive()` handle. `stop` is now
  idempotent through `Ref`, so explicit stop and scoped finalizers do not close
  workers twice.
- The request-response stop signal slice added a `Deferred` shutdown signal to
  `makeEffectRequestResponseFromPubSub`. Pending requests now race response
  waiting against runtime stop and fail promptly with a tagged
  `MessagingLifecycleError` instead of waiting for timeout.
- The legacy consumer facade slice moved `makeConsumer` onto
  `makeEffectConsumerFromPubSub` with a `ManagedRuntime` Promise boundary and a
  closeable `Scope`. Consumer workers now use `Effect.forkScoped` so their
  lifetime is owned by the caller scope rather than the parent fiber. The
  `Effect.runPromise`, `receive(`, `new Promise`, and `setTimeout` counts
  dropped because the old blocking facade loop and its test timer shim were
  removed.
- The workbench theme storage slice stopped mirroring `themeAtom` into the
  legacy `tg-theme` localStorage key. The canonical
  `trustgraph-workbench-theme-v1` value remains owned by `Atom.kvs` over
  `BrowserKeyValueStore.layerLocalStorage`; the first-paint host script reads
  that JSON-encoded key before React mounts and falls back to `tg-theme` only
  for legacy installs.
- The Effect AI `LanguageModel` adapter slice added a reusable
  `makeLanguageModelProvider` bridge in text-completion common code. It maps
  `generateText` responses to `LlmResult`, maps streaming `text-delta` and
  final `finish.usage` parts to TrustGraph chunks, and converts Effect AI rate
  and quota failures into `TooManyRequestsError`. No concrete provider has
  been flipped yet.
- The native request/response PubSub slice removed the local
  `Map<string, Queue>` response subscriber fanout in
  `makeEffectRequestResponseFromPubSub`. Response dispatch now publishes
  `{ id, value }` envelopes through native `effect/PubSub`, and each request
  uses a scoped `PubSub.Subscription` plus `Stream.fromSubscription` to wait
  for its matching response.
- The Claude Effect AI slice moved the Claude provider off the direct
  `@anthropic-ai/sdk` wrapper and onto `@effect/ai-anthropic`
  `AnthropicLanguageModel` through `makeLanguageModelProvider`. The direct SDK
  dependency was removed from `@trustgraph/flow`.
- A focused broker-backend scout found no remaining P0 broker runtime rewrite
  after the producer, NATS, consumer concurrency, rate-limit, and
  request-response stop slices. `PubSubBackend` remains an intentional
  Promise-returning adapter boundary wrapped by `PubSub`/Effect services.
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
- The client socket close Effect boundary slice removed the Promise `.catch`
  from `BaseApi.close()`. The void public facade now runs `rpc.close()` through
  `Effect.tryPromise` and logs the tagged socket close error through
  `Effect.catch`.
- The client streaming callback Effect boundary slice removed the remaining
  production Promise `.catch` matches from `trustgraph-socket.ts` by
  centralizing legacy callback request failures in `runLegacyStreamingRequest`.
  The public callback facades still return/ignore Promises where required, but
  failure mapping now uses `Effect.tryPromise` and `Effect.catch`.
- The text completion provider effectful layer slice dropped six
  `Layer.succeed` matches by moving OpenAI, OpenAI-compatible, Azure OpenAI,
  Claude, Mistral, and Ollama processor layers onto
  `makeTextCompletionLayer(makeXProviderEffect(config))`. SDK construction and
  config lookup now live in Effect; sync `makeXProvider` exports remain
  compatibility facades.
- The gateway dispatcher ownership and serialization slice did not change broad
  signal counts. It stopped closing injected pubsub backends, brackets
  one-shot publish producers with `Effect.acquireUseRelease`, and routes
  gateway request/response translation through `Effect.try` wrappers returning
  tagged `DispatchSerializationError` failures.
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

### 2026-06-02: Client Socket Close Effect Boundary Slice

- Status: migrated and root-verified.
- Completed:
  - `ts/packages/client/src/socket/trustgraph-socket.ts` now wraps
    `rpc.close()` with `Effect.tryPromise` inside the public `close(): void`
    facade.
  - Close failures are mapped to the existing tagged `TrustGraphSocketError`
    shape and logged through `Effect.catch` instead of a Promise `.catch`.
  - The remaining client socket Promise `.catch` matches were streaming
    callback compatibility bridges and are now handled by the follow-up slice.
- Verification:
  - `cd ts && bun run check:tsgo`
  - `bun run --cwd ts/packages/client build`
  - `bun run --cwd ts/packages/client test`
  - `cd ts && bun run check`
  - `cd ts && bun run build`
  - `cd ts && bun run test`
  - `git diff --check`

### 2026-06-02: Client Streaming Callback Effect Boundary Slice

- Status: migrated and root-verified.
- Completed:
  - `ts/packages/client/src/socket/trustgraph-socket.ts` now routes the
    legacy `agent`, `graphRagStreaming`, and `documentRagStreaming` callback
    request failures through `runLegacyStreamingRequest`.
  - `runLegacyStreamingRequest` uses `Effect.tryPromise` to map failures into
    tagged `TrustGraphSocketError` values, then uses `Effect.catch` to invoke
    the public legacy error callback.
  - Production `trustgraph-socket.ts` no longer has Promise `.catch` matches;
    remaining matches in that file are `Effect.catch` only.
  - Rechecked the PubSub replacement question against Effect v4 source:
    Effect's native `PubSub` is an in-process async hub over Effect queues.
    TrustGraph's `PubSubBackend` remains the broker adapter boundary for
    NATS/Pulsar-style topics, subscriptions, acknowledgement, schema codecs,
    and backend lifecycle.
- Verification:
  - `cd ts && bun run check:tsgo`
  - `bun run --cwd ts/packages/client build`
  - `bun run --cwd ts/packages/client test`
  - `cd ts && bun run check`
  - `cd ts && bun run build`
  - `cd ts && bun run test`
  - `git diff --check`

### 2026-06-02: Text Completion Provider Effectful Layer Slice

- Status: migrated and root-verified.
- Completed:
  - Added shared `makeTextCompletionLayer` for constructing `Llm` from an
    effectful `LlmProvider`.
  - Added `makeOpenAIProviderEffect`,
    `makeOpenAICompatibleProviderEffect`, `makeAzureOpenAIProviderEffect`,
    `makeClaudeProviderEffect`, `makeMistralProviderEffect`, and
    `makeOllamaProviderEffect`.
  - Processor `program.layer` definitions now use `Layer.effect` via the
    shared helper instead of constructing providers inside `Layer.succeed`.
  - Provider object assembly is split into pure `makeXProviderFromClient`
    helpers so Promise-returning provider methods remain external
    compatibility facades and do not trigger `effect(runEffectInsideEffect)`.
  - Added tests for explicit provider config, shared `Llm` layer provisioning,
    and tagged missing-config errors.
- Verification:
  - `bunx --bun vitest run src/__tests__/text-completion-providers.test.ts src/__tests__/text-completion-common.test.ts`
  - `bun run --cwd ts/packages/flow build`
  - `bun run --cwd ts/packages/flow test`
  - `cd ts && bun run check:tsgo`
  - `cd ts && bun run check`
  - `cd ts && bun run build`
  - `cd ts && bun run test`
  - `git diff --check`

### 2026-06-02: Gateway Dispatcher Ownership And Serialization Slice

- Status: migrated and root-verified.
- Completed:
  - `makeDispatcherManager` now tracks whether it owns the pubsub backend and
    no longer closes injected `PubSubBackend` instances on `stop()`.
  - `publishToTopic` now uses `Effect.acquireUseRelease` so the one-shot
    producer is closed even when `send` fails.
  - Gateway dispatch paths now call `translateRequestEffect` and
    `translateResponseEffect`, which wrap serialization with `Effect.try` and
    return tagged `DispatchSerializationError` failures.
  - Streaming dispatch recipients are named `Effect.fn` callbacks, satisfying
    strict Effect diagnostics while preserving responder behavior.
  - Tests cover injected backend ownership, typed serialization failure before
    requestor startup, and producer close on send failure.
- Verification:
  - `bunx --bun vitest run src/__tests__/gateway-dispatcher.test.ts`
  - `bun run --cwd ts/packages/flow build`
  - `bun run --cwd ts/packages/flow test`
  - `cd ts && bun run check:tsgo`
  - `cd ts && bun run check`
  - `cd ts && bun run build`
  - `cd ts && bun run test`
  - `git diff --check`

### 2026-06-02: Base Producer Scoped Runtime Slice

- Status: migrated and root-verified.
- Completed:
  - Kept `PubSubBackend` as the broker adapter boundary; Effect native
    `PubSub` remains an in-process primitive and is not a replacement for
    broker-backed topics, subscriptions, acknowledgements, codecs, or backend
    lifecycle.
  - Reworked `makeProducer` so the legacy Promise facade allocates producers
    through `makeEffectProducerFromPubSub` inside a closeable `Scope`.
  - `stop()` now flushes the Effect producer and closes the scope with the
    registered producer finalizer, including the flush-failure path.
  - Added focused producer facade coverage for send routing, idempotent stop,
    tagged not-started lifecycle errors, and close-on-flush-failure behavior.
- Verification:
  - `cd ts && bun run check:tsgo`
  - `bun run --cwd ts/packages/base build`
  - `cd ts/packages/base && bunx --bun vitest run src/__tests__/producer.test.ts`
  - `bun run --cwd ts/packages/base test`
  - `cd ts && bun run check`
  - `cd ts && bun run build`
  - `cd ts && bun run test`

### 2026-06-02: NATS Typed Boundary Slice

- Status: migrated and root-verified.
- Completed:
  - Replaced the dynamic header import inside `makeNatsProducer` with the
    static NATS `headers` export.
  - Wrapped publish header construction in `Effect.try`, so invalid header
    names/values fail as tagged `PubSubError` values instead of defects.
  - Wrapped NATS `ack()` and `nak()` calls in `Effect.try`, preserving the
    existing wrong-message guard and mapping thrown acknowledgement failures
    into tagged `PubSubError`s.
  - Added a mocked NATS backend test covering invalid publish headers and
    thrown ack/nak failures through the public `makeNatsBackend` path.
- Verification:
  - `cd ts && bun run check:tsgo`
  - `cd ts/packages/base && bunx --bun vitest run src/__tests__/nats-backend.test.ts`
  - `bun run --cwd ts/packages/base build`
  - `bun run --cwd ts/packages/base test`
  - `cd ts && bun run check`
  - `cd ts && bun run build`
  - `cd ts && bun run test`

### 2026-06-02: NATS Selective 404 Slice

- Status: migrated and root-verified.
- Completed:
  - Added an internal `NatsLookupError` tagged error to preserve lookup causes
    without leaving `unknown` in Effect error channels.
  - Stream creation now happens only when `manager.streams.info()` fails with
    a NATS JetStream 404/missing-resource error.
  - Durable consumer creation now happens only when `js.consumers.get()` fails
    with a NATS JetStream 404/missing-resource error.
  - Added mocked NATS tests proving 404 lookups create resources while
    permission-style lookup failures do not.
- Verification:
  - `cd ts && bun run check:tsgo`
  - `cd ts/packages/base && bunx --bun vitest run src/__tests__/nats-backend.test.ts`
  - `bun run --cwd ts/packages/base build`
  - `bun run --cwd ts/packages/base test`
  - `cd ts && bun run check`
  - `cd ts && bun run build`
  - `cd ts && bun run test`

### 2026-06-02: Consumer Rate-Limit Retry Slice

- Status: migrated and root-verified.
- Completed:
  - Added `rateLimitTimeoutMs` to the Effect-native messaging runtime config,
    backed by `TG_RATE_LIMIT_TIMEOUT_MS` and the Python-compatible default of
    `7_200_000ms`.
  - Reworked legacy `makeConsumer` retry handling to use `Schedule.spaced`,
    retry repeated `TooManyRequestsError`s, and fail with a tagged
    `MessagingTimeoutError` when the rate-limit timeout elapses.
  - Reworked `makeEffectConsumerFromPubSub` handler retry handling with the
    same schedule/timeout behavior while keeping handler failures in typed
    Effect error channels.
  - Added legacy and Effect-native tests for repeated rate-limit retry until
    success and negative acknowledgement after retry timeout.
- Verification:
  - `cd ts && bun run check:tsgo`
  - `cd ts/packages/base && bunx --bun vitest run src/__tests__/consumer.test.ts src/__tests__/messaging-runtime.test.ts`
  - `bun run --cwd ts/packages/base build`
  - `bun run --cwd ts/packages/base test`
  - `cd ts && bun run check`
  - `cd ts && bun run build`
  - `cd ts && bun run test`

### 2026-06-02: Consumer Concurrency Ownership Slice

- Status: migrated and root-verified.
- Completed:
  - `makeEffectConsumerFromPubSub` now creates one backend consumer per
    concurrency worker rather than sharing a single backend consumer across
    parallel receive loops.
  - Consumer runtime `stop` is idempotent via `Ref.getAndSet`, so explicit
    `consumer.stop` and scope finalization do not double-close worker handles.
  - Added Effect-native runtime coverage proving `concurrency: 3` creates and
    closes three independent backend consumers exactly once.
- Verification:
  - `cd ts && bun run check:tsgo`
  - `cd ts/packages/base && bunx --bun vitest run src/__tests__/messaging-runtime.test.ts`
  - `bun run --cwd ts/packages/base build`
  - `bun run --cwd ts/packages/base test`
  - `cd ts && bun run check`
  - `cd ts && bun run build`
  - `cd ts && bun run test`

### 2026-06-02: Request-Response Stop Signal Slice

- Status: migrated and root-verified.
- Completed:
  - `makeEffectRequestResponseFromPubSub` now owns a `Deferred` stop signal for
    the lifetime of the scoped request-response runtime.
  - `request()` races response waiting against that stop signal before applying
    the request timeout, so pending calls fail promptly when the runtime stops.
  - `stop()` fails the stop signal with a tagged `MessagingLifecycleError`
    before interrupting the dispatch loop and closing the producer/consumer
    resources.
  - Flow PDF decoder and graph embeddings service error unions now include
    `MessagingLifecycleError` because requestor failures can surface shutdown.
  - Added Effect-native runtime coverage proving a pending request fails with
    the tagged lifecycle error when the request-response runtime stops.
- Verification:
  - `cd ts && bun run check:tsgo`
  - `cd ts/packages/base && bunx --bun vitest run src/__tests__/messaging-runtime.test.ts`
  - `bun run --cwd ts/packages/base build`
  - `bun run --cwd ts/packages/base test`
  - `bun run --cwd ts/packages/flow build`
  - `bun run --cwd ts/packages/flow test`
  - `cd ts && bun run check`
  - `cd ts && bun run build`
  - `cd ts && bun run test`

### 2026-06-02: Legacy Consumer Facade Slice

- Status: migrated and root-verified.
- Completed:
  - `makeConsumer` is now a Promise compatibility facade over
    `makeEffectConsumerFromPubSub` instead of owning a separate mutable
    backend, `running` flag, retry loop, and direct `BackendConsumer.receive`.
  - The facade uses a module `ManagedRuntime`, `Scope.make`, `Scope.provide`,
    and `Scope.close` to keep public `start()`/`stop()` Promises at the
    boundary while the actual consumer lifetime stays scoped.
  - Legacy Promise handlers are adapted with `Effect.tryPromise` and preserve
    `TooManyRequestsError` as a typed retry signal.
  - `makeEffectConsumerFromPubSub` now forks workers with `Effect.forkScoped`,
    so a caller-owned scope keeps workers alive until stop/finalization.
  - `consumer.test.ts` no longer encodes `start()` as the blocking consume-loop
    join; it waits for observable handler/ack/nak effects and then stops the
    scoped consumer.
- Verification:
  - `cd ts/packages/base && bunx --bun vitest run src/__tests__/consumer.test.ts`
  - `cd ts/packages/base && bunx --bun vitest run src/__tests__/messaging-runtime.test.ts src/__tests__/flow-spec-runtime.test.ts`
  - `cd ts && bun run check:tsgo`
  - `bun run --cwd ts/packages/base build`
  - `bun run --cwd ts/packages/base test`
  - `cd ts && bun run check`
  - `cd ts && bun run build`
  - `cd ts && bun run test`
  - `git diff --check`

### 2026-06-02: Workbench Theme KeyValueStore Slice

- Status: migrated and root-verified.
- Completed:
  - `themeClassAtom` no longer writes the legacy `tg-theme` localStorage
    mirror. Theme persistence stays in the canonical
    `trustgraph-workbench-theme-v1` `Atom.kvs` entry backed by
    `BrowserKeyValueStore.layerLocalStorage`.
  - The pre-paint host script in `index.html` now restores the canonical
    JSON-encoded theme key before React mounts, with `tg-theme` retained only
    as a legacy fallback.
  - Workbench QA now asserts that changing theme writes the canonical key and
    does not recreate `tg-theme`.
- Verification:
  - `cd ts && bun run check`
  - `cd ts && bun run workbench:qa`
  - `cd ts && bun run build`
  - `cd ts && bun run test`
  - `cd ts && bun run lint`

### 2026-06-02: Effect AI LanguageModel Adapter Slice

- Status: migrated and package-verified.
- Completed:
  - Added `makeLanguageModelProvider`, a bridge from
    `effect/unstable/ai/LanguageModel` into the existing TrustGraph
    `LlmProvider` contract.
  - Covered non-streaming text/token mapping, streaming text/final-token
    mapping, and Effect AI rate/quota failure mapping with fake
    `LanguageModel` tests.
  - Kept concrete provider swaps deferred until provider-specific parity is
    proven.
- Verification:
  - `cd ts && bun run check:tsgo`
  - `cd ts/packages/flow && bunx --bun vitest run src/__tests__/text-completion-common.test.ts src/__tests__/text-completion-providers.test.ts`

### 2026-06-02: Native Request/Response PubSub Fanout Slice

- Status: migrated and package-verified.
- Completed:
  - Replaced the request/response runtime's hand-managed
    `Map<string, Queue>` response fanout with native `effect/PubSub`.
  - Each request subscribes before sending, consumes through
    `Stream.fromSubscription`, filters by response id, and releases the
    subscription at scope exit.
  - Kept `PubSubBackend` as the broker boundary because Effect native PubSub is
    in-process only and does not provide NATS topics, ack/nack, durable
    subscriptions, schema codecs, or backend lifecycle.
- Verification:
  - `cd ts && bun run check:tsgo`
  - `cd ts/packages/base && bunx --bun vitest run src/__tests__/messaging-runtime.test.ts src/__tests__/request-response.test.ts src/__tests__/flow-spec-runtime.test.ts`

### 2026-06-02: Claude Effect AI Provider Slice

- Status: migrated and package-verified.
- Completed:
  - Replaced the direct `@anthropic-ai/sdk` provider implementation with
    `@effect/ai-anthropic` `AnthropicLanguageModel` plus the shared
    `makeLanguageModelProvider` adapter.
  - Preserved `CLAUDE_KEY`, default model, temperature, max output, processor,
    and public `LlmProvider` compatibility behavior.
  - Added Claude provider config coverage for `CLAUDE_KEY` env fallback and the
    missing-key tagged config error.
  - Removed the direct `@anthropic-ai/sdk` dependency and its lockfile entries
    from `@trustgraph/flow`.
- Verification:
  - `cd ts && bun run check:tsgo`
  - `cd ts/packages/flow && bunx --bun vitest run src/__tests__/text-completion-providers.test.ts src/__tests__/text-completion-common.test.ts`
  - `cd ts/packages/flow && bun run build`
  - `cd ts && bun run check`
  - `cd ts && bun run build`
  - `cd ts && bun run test`
  - `cd ts && bun run lint`
  - `git diff --check`

### 2026-06-02: RPC Dispatch Tagged Error Slice

- Status: migrated and package-verified.
- Completed:
  - Replaced the remaining production `S.ErrorClass` usage in the Flow gateway
    RPC contract with `S.TaggedErrorClass`.
  - Normalized the client-side RPC `DispatchError` counterpart to the same
    tagged-error schema shape so both wire contract copies stay aligned.
  - Closed the scratch-note `S.ErrorClass` finding for production code. The
    remaining plain `new Error` matches are test-only helpers or external
    host-boundary simulations.
- Verification:
  - `cd ts && bun run check:tsgo`
  - `cd ts/packages/flow && bunx --bun vitest run src/__tests__/gateway-dispatcher.test.ts`
  - `cd ts/packages/client && bunx --bun vitest run src/__tests__/rpc-timeout.test.ts`
  - `cd ts && bun run check`
  - `cd ts && bun run build`
  - `cd ts && bun run test`
  - `cd ts && bun run lint`
  - `git diff --check`

### 2026-06-02: Effect Metrics Prometheus Slice

- Status: migrated and root-verified.
- Completed:
  - Replaced the `@trustgraph/base` `prom-client` metric wrappers with
    Effect-native `Metric.counter`, `Metric.histogram`, and
    `effect/unstable/observability` `PrometheusMetrics.format`.
  - Kept the existing Prometheus metric names and gateway
    `/api/v1/metrics` scrape boundary while removing the direct `prom-client`
    dependency and lockfile entries.
  - Changed producer metric recording from a sync callback to an Effect value
    that runs inside the producer send pipeline.
  - Added isolated metric-registry tests for producer and consumer Prometheus
    formatting.
- Verification:
  - `cd ts && bun run check:tsgo`
  - `cd ts/packages/base && bunx --bun vitest run src/__tests__/metrics-effect.test.ts src/__tests__/producer.test.ts src/__tests__/messaging-runtime.test.ts`
  - `cd ts/packages/base && bun run build`
  - `cd ts/packages/base && bun run test`
  - `cd ts/packages/flow && bun run build`
  - `cd ts/packages/flow && bunx --bun vitest run src/__tests__/gateway-dispatcher.test.ts`
  - `cd ts && bun run check`
  - `cd ts && bun run build`
  - `cd ts && bun run test`
  - `cd ts && bun run lint`
  - `git diff --check`

### 2026-06-02: MCP Effect Stdio Entrypoint Slice

- Status: migrated and root-verified.
- Completed:
  - Added an Effect-native stdio layer and process entrypoint with
    `McpServer.layerStdio`, `NodeStdio.layer`, and `NodeRuntime.runMain`.
  - Reused the same `TrustGraphMcpToolkitLive` path for HTTP and stdio through
    a shared toolkit-layer helper.
  - Kept the legacy SDK/Zod stdio export as a compatibility surface until
    protocol-level `tools/list` and `tools/call` parity tests prove it can be
    flipped or removed.
  - Added focused coverage that the Effect toolkit names remain stable and
    the stdio layer/entrypoint are exported.
  - Updated the MCP test script to ignore compiled `dist/**` output so root
    builds do not cause duplicate Vitest runs from generated tests.
- Scratch-note triage:
  - Metrics, in-process PubSub fanout, Claude Effect AI, RPC
    `S.TaggedErrorClass`, and `@effect/tsgo` setup are already migrated.
  - Remaining valid scratch targets are MCP protocol parity/flip, Duration
    config cleanup, Term/ClientTerm tagged-union matching, service
    `Effect.fn` normalization, `@effect/cli`, stream/RPC follow-ups, chunking
    `Chunk`, cores Promise APIs, and long-lived `Map`/`Set` state.
- Verification:
  - `cd ts/packages/mcp && bun run test`
  - `cd ts/packages/mcp && bun run build`
  - `cd ts && bun run check:tsgo`
  - `cd ts && bun run build`
  - `cd ts && bun run test`
  - `cd ts && bun run lint`
  - `git diff --check`

### 2026-06-02: Term And ClientTerm Match Slice

- Status: migrated and package-verified.
- Completed:
  - `ts/packages/base/src/schema/primitives.ts` now exposes `Term` as a
    recursive `S.toTaggedUnion("type")` schema and aligns `Triple.g` with the
    Python/client wire contract as an optional graph string.
  - `ts/packages/flow/src/gateway/dispatch/serialize.ts` now defines compact
    client-term schemas with `S.tag`, decodes unknown term-shaped values with
    Schema/Option, and translates terms with
    `Match.discriminatorsExhaustive`.
  - Removed the gateway serializer's native term switches and unsafe
    pass-through casts. Malformed known-tag objects now stay ordinary payload
    objects during deep translation instead of being cast into invalid terms.
  - Replaced pure term helper switches in FalkorDB triples store/query,
    Qdrant graph embeddings store, Graph RAG, agent tools, and workbench graph
    utilities with exhaustive `Match` discriminators.
  - Added tests for named graph string decoding, nested compact/internal term
    round trips, and malformed known-tag payload preservation.
- Remaining:
  - The client socket streaming term schema is still a local recursive union
    and can be centralized later if drift appears. It has no native term
    switch in the current scan.
  - Operation dispatch switches in config, cores, librarian, and flow-manager
    are separate service-command refactors, not part of this term wire slice.
- Verification:
  - `cd ts && bun run check:tsgo`
  - `cd ts/packages/base && bunx --bun vitest run src/__tests__/schema-effect.test.ts`
  - `cd ts/packages/flow && bunx --bun vitest run src/__tests__/gateway-dispatcher.test.ts src/__tests__/falkordb-lifecycle.test.ts src/__tests__/qdrant-embeddings.test.ts src/__tests__/retrieval-rag.test.ts`
  - `cd ts/packages/flow && bun run test`
  - `cd ts/packages/base && bun run build`
  - `cd ts/packages/flow && bun run build`
  - `cd ts/packages/workbench && bun run build`
  - `cd ts && bun run build`
  - `cd ts && bun run test`
  - `cd ts && bun run lint`
  - `git diff --check`

## Subagent Findings To Preserve

- MCP/workbench:
  - Make the Effect MCP server the canonical implementation. An Effect
    `McpServer.layerStdio` entrypoint now exists; the old stdio server should
    remain only as compatibility until protocol-level `tools/list` and
    `tools/call` parity is proved. Do not delete `server.ts` until that parity
    coverage exists, with special attention to `text_completion` behavior.
  - Workbench BaseApi atoms can move toward `AtomRpc` or `AtomHttpApi` after
    the client API is less Promise-first.
  - MCP env is now Config-backed; continue that policy for future MCP settings.
  - Workbench persistent theme storage is now canonicalized through
    `Atom.kvs`/`BrowserKeyValueStore`. Remaining workbench `localStorage`
    matches are legacy migration fallbacks, QA assertions, or the pre-paint
    host script.
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
  - The legacy producer and consumer facades now delegate to scoped Effect
    runtime factories. Public `start()`/`send()`/`stop()` Promises remain
    compatibility boundaries.
  - NATS header construction, ack/nak operations, and lookup create-on-missing
    behavior now stay typed. `PubSubBackend` remains an intentional broker
    adapter contract rather than a direct `effect/PubSub` replacement target.
  - Consumer rate-limit retry timeout behavior is now wired in both legacy and
    Effect-native consumer paths. Effect-native consumer concurrency now owns
    one backend consumer per worker, and request-response pending shutdown now
    fails through a tagged lifecycle error. The legacy consumer facade blocking
    shape is complete; do not reopen it unless a public API compatibility
    issue appears.
  - Existing constructor shims preserve callable-plus-newable public exports;
    removing them needs a public API split or real class redesign.
  - Typed string registries in `Flow` now have Schema-backed parameter specs
    and typed producer/requestor spec-object accessors. New service handlers
    should hoist spec objects and use those accessors; bare string accessors
    remain compatibility escapes.
  - Base metrics are now Effect-native and Prometheus-formatted through
    `PrometheusMetrics.format`; do not reopen `prom-client` unless a future
    scrape requirement cannot be represented by Effect metrics.
  - Numeric public timeout fields such as `timeoutMs` remain compatibility
    surfaces. Internal runtime config with `Config.number(...Ms)` is still a
    valid `Config.duration` / `Duration` cleanup target.
- Gateway/client:
  - `EffectRpcClient` now owns its socket/RPC layer with `ManagedRuntime`.
    Socket errors/JSON parsing now use tagged errors and Schema decoding.
    The remaining client `newableFactory` assertions are documented as public
    API compatibility boundaries for this loop.
  - Gateway/client `DispatchError` contracts now use `S.TaggedErrorClass`; do
    not reopen `S.ErrorClass` unless a new production match appears.
  - Gateway `DispatchStream` now uses Effect-native dispatcher streaming
    callbacks instead of nested `Effect.runPromiseWith`, and client streaming
    facade callbacks now decode the legacy envelope through Schema before
    applying service-specific public callback semantics.
  - Gateway dispatcher ownership and serialization cleanup is complete:
    injected pubsub backends are not closed by the manager, one-shot producers
    are acquire/use/release bracketed, and serialization failures are typed
    Effect errors.
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
    text, token counts, streaming final usage, and rate-limit mapping. The
    local provider layer-construction cleanup is complete; remaining provider
    work is adapter/parity work, not `Layer.succeed` cleanup.
  - The `effect/unstable/ai/LanguageModel` to TrustGraph `LlmProvider` adapter
    baseline is complete, and Claude now uses `@effect/ai-anthropic` through
    that adapter. Direct OpenAI, Azure, and OpenAI-compatible swaps are no-ops
    until Responses-vs-Chat-Completions parity is proven.
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
- Scratch-note follow-ups:
  - `Term` / compact client term serialization is complete for base schema,
    gateway translation, and pure term helper switches. Future work should
    only reopen this if client socket schema drift appears or a hidden
    consumer needs a different named-graph shape.
  - Messaging runtime `Config.duration` is the next strongest scratch target:
    internal runtime config can use `Duration.Duration` while public
    `timeoutMs` compatibility surfaces stay numeric.
  - Qdrant graph/doc known-collection caches are a good small
    `MutableHashSet<string>` candidate; short-lived local traversal sets
    remain no-ops.
  - FlowManager and sibling service `() => Effect.gen(...)` factories remain a
    broad mechanical `Effect.fn` / `Effect.fnUntraced` cleanup, best handled
    after Duration and small collection slices.
  - Long-lived `Map` / `Set` state in ref-backed services can move toward
    Effect collections later; static lookup tables and local pure traversal
    maps/sets remain no-ops.

## Ranked Findings

### No-op: Broker Backend Adapter Boundary

- Status:
  - Closed as a P0 rewrite item after the 2026-06-02 broker scout and the
    legacy consumer facade slice.
- TrustGraph evidence:
  - `ts/packages/base/src/backend/types.ts`
  - `ts/packages/base/src/backend/nats.ts`
  - `ts/packages/base/src/backend/pubsub.ts`
  - `ts/packages/base/src/messaging/runtime.ts`
- Effect primitives:
  - `Layer`, `Scope`, `Stream`, `Schedule`, `Queue`,
    `Effect.acquireRelease`, and `Effect.tryPromise`.
- Evidence:
  - `BackendProducer`, `BackendConsumer`, and `PubSubBackend` are the external
    Promise broker adapter contract. `backend/pubsub.ts` wraps that contract in
    Effect through `Context.Service`, `Layer`, `Effect.tryPromise`, and scoped
    finalizers.
  - NATS boundary failures, selective stream/consumer lookup recovery,
    producer sends, ack/nak, and close paths are typed with Effect wrappers.
  - Producer, consumer, and request-response runtime ownership now live in
    scoped Effect factories.
- Rule:
  - Keep `PubSubBackend` as the compatibility adapter boundary; Effect native
    `PubSub` remains in-process only.
  - Treat the producer Promise facade as a completed compatibility wrapper;
    avoid reopening it unless backend runtime changes require a narrower
    adapter.
  - Keep NATS SDK boundary failures typed and avoid catch-all
    create-on-failure behavior. Future backend slices should move
    connection/stream state into scoped Effect services.
  - Treat rate-limit retry timeout semantics as complete; next consumer slices
    should focus on blocking compatibility and backend/layer ownership, not
    retry policy.
  - Treat Effect-native per-worker consumer ownership as complete; do not flag
    `makeEffectConsumerFromPubSub` concurrency for shared backend receive
    handles.
  - Treat request-response pending shutdown semantics as complete; do not flag
    `waitForResponse` timeout behavior for stopped runtimes.
  - Treat request-response in-process fanout as complete: response routing now
    uses native `effect/PubSub` subscriptions instead of a hand-managed
    subscriber map.
  - Treat the legacy consumer facade as a completed compatibility wrapper over
    `makeEffectConsumerFromPubSub`; do not flag blocking `start()` semantics.

### No-op: Remaining Effect AI Provider Swaps

- TrustGraph evidence:
  - `ts/packages/flow/src/model/text-completion/*.ts`
- Effect primitives:
  - `effect/unstable/ai/LanguageModel`, `effect/unstable/ai/EmbeddingModel`,
    Effect AI OpenAI/Anthropic provider layers.
- Rewrite shape:
  - Adapter baseline is complete: `makeLanguageModelProvider` bridges
    `LanguageModel` into `LlmProvider`.
  - Claude migration is complete through `@effect/ai-anthropic`.
  - Do not directly swap OpenAI, Azure, or OpenAI-compatible providers yet:
    current TrustGraph code uses Chat Completions/local-server semantics while
    `@effect/ai-openai` is Responses API backed.
  - Do not directly swap Mistral or Ollama until an installed Effect provider
    package exists or a parity-backed local Effect wrapper is designed.
- Tests:
  - Provider parity for `LlmResult`, final streaming chunk token counts, 429
    mapping, missing-token config failures, and OpenAI-compatible local-server
    behavior.

### No-op: Base Metrics Prometheus Wrapper

- Status:
  - Closed as a scratch-note migration target by the Effect Metrics Prometheus
    slice.
- TrustGraph evidence:
  - `ts/packages/base/src/metrics/prometheus.ts`
  - `ts/packages/flow/src/gateway/server.ts`
- Effect primitives:
  - `Metric.counter`, `Metric.histogram`, and
    `effect/unstable/observability` `PrometheusMetrics.format`.
- Rule:
  - Keep the gateway Fastify route as the external scrape boundary, but record
    TrustGraph metrics through Effect `Metric` values.
  - Use a fresh `Metric.MetricRegistry` in tests that assert exact scrape
    content.

### Complete: Term And ClientTerm Tagged-Union Normalization

- TrustGraph evidence:
  - `ts/packages/base/src/schema/primitives.ts`
  - `ts/packages/flow/src/gateway/dispatch/serialize.ts`
  - `ts/packages/client/src/socket/trustgraph-socket.ts`
- Effect primitives:
  - `S.toTaggedUnion(...).match` and `effect/Match` discriminator helpers.
- Rewrite shape:
  - Add tagged-union helpers for internal `Term` and compact client terms.
  - Replace serializer native switches with tagged-union matching or
    `Match.discriminatorsExhaustive`.
  - Remove unsafe default pass-through casts while preserving compact `g`
    string compatibility.
- Tests:
  - Base schema tests now cover recursive terms and graph strings.
  - Gateway dispatcher tests now cover all compact term variants, nested
    triples, compact graph strings, malformed known-tag payloads, and
    malformed client triple failures.

### P1: Messaging Runtime Duration Config Cleanup

- TrustGraph evidence:
  - `ts/packages/base/src/runtime/messaging-config.ts`
  - `ts/packages/base/src/messaging/runtime.ts`
- Effect primitives:
  - `Config.duration`, `Duration.Duration`, and existing `Duration.millis`
    compatibility conversions.
- Rewrite shape:
  - Change internal runtime config fields such as `receiveTimeoutMs`,
    `requestTimeoutMs`, `retryDelayMs`, and `rateLimitTimeoutMs` to
    `Duration.Duration`.
  - Load env-backed values with `Config.duration` while preserving Python-style
    millisecond defaults and public numeric compatibility options.
  - Keep external `timeoutMs` option names numeric in request/response,
    processor, and client boundaries unless their public API is deliberately
    changed.
- Tests:
  - Extend base runtime config tests for env duration parsing and verify
    messaging retry/timeout behavior still uses the same effective durations.

### P2: Qdrant Known-Collection MutableHashSet Cleanup

- TrustGraph evidence:
  - `ts/packages/flow/src/storage/embeddings/qdrant-doc.ts`
  - `ts/packages/flow/src/storage/embeddings/qdrant-graph.ts`
- Effect primitives:
  - `MutableHashSet` from `effect`.
- Rewrite shape:
  - Replace long-lived `Set<string>` known-collection caches with
    `MutableHashSet<string>` in Qdrant graph/doc embedding stores.
  - Keep short-lived local `Set` values for pure query traversal or fixture
    assertions as no-op boundaries.
- Tests:
  - Existing Qdrant embeddings tests should prove lazy collection creation and
    deletion cache invalidation still behave the same.

### P2: Canonicalize MCP Around The Effect Server

- Status:
  - MCP now builds under strict tsgo, the stdio server has an Effect-backed
    compatibility implementation, and an Effect `McpServer.layerStdio`
    entrypoint exists.
- Remaining shape:
  - Keep the old SDK/Zod stdio compatibility surface for now.
  - Prove `tools/list` and `tools/call` parity before deleting any public
    entry point or dropping `zod`/server-side MCP SDK dependencies.
  - Pay special attention to `text_completion`: legacy calls the TrustGraph
    gateway, while the Effect server currently uses an Effect AI
    `LanguageModel`/OpenAI layer.
- Tests:
  - `cd ts && bun run --cwd packages/mcp build`
  - Root `cd ts && bun run check`

### No-op: Workbench Theme And Browser Storage Boundaries

- Status: migrated and documented no-op for remaining direct browser matches.
- Evidence:
  - `settingsAtom`, `themeAtom`, `flowIdAtom`, and `conversationAtom` are
    canonical `Atom.kvs` entries backed by
    `BrowserKeyValueStore.layerLocalStorage`.
  - The only remaining `tg-theme` production read is a legacy migration
    fallback. The pre-paint `index.html` script is a host boundary that restores
    the canonical key before React and Effect services mount.
  - Graph canvas DOM/class inspection remains render-only host behavior.
- Rule:
  - Do not reopen workbench `localStorage` as a backend/runtime blocker unless
    a canonical `Atom.kvs` entry is bypassed or a legacy migration fallback can
    be intentionally removed.

## Recommended PR Order

1. Messaging runtime `Config.duration` / `Duration` cleanup.
2. Qdrant known-collection `MutableHashSet` cleanup.
3. MCP protocol parity tests and legacy stdio flip/removal decision.
4. FlowManager/service `Effect.fn` normalization.

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
- Workbench pre-paint `index.html` storage reads are host-boundary code used
  before React and Effect services mount. Keep canonical workbench state in
  `Atom.kvs`/`BrowserKeyValueStore`, and treat old-key reads as migration
  fallbacks unless backward compatibility is intentionally dropped.
- The old MCP SDK/Zod stdio server is compatibility code until an Effect stdio
  entrypoint plus parity tests prove the same public protocol behavior.
- Client `newableFactory` assertions that preserve vendored callable-plus-new
  API facades are compatibility boundaries unless the public constructor API is
  intentionally redesigned.
- Base `AsyncProcessor`, `Flow`, and `FlowProcessor` callable-plus-newable
  export assertions are compatibility boundaries unless the public constructor
  API is intentionally redesigned.
- TrustGraph `PubSubBackend` / backend `PubSub` service is a broker adapter
  boundary for NATS/Pulsar-style topics, acknowledgement, schema codecs, and
  backend lifecycle. Effect's native `PubSub` can replace in-process fanout
  helpers, but not the distributed broker abstraction by itself. This was
  rechecked against
  `/home/elpresidank/YeeBois/projects/beep-effect2/.repos/effect-v4/packages/effect/src/PubSub.ts`,
  whose exported API is local publish/subscribe over Effect queues.
- Request-response pending shutdown semantics are complete in
  `makeEffectRequestResponseFromPubSub`: pending calls race response waiting
  against a `Deferred` stop signal and fail with tagged
  `MessagingLifecycleError`.
- Legacy `makeConsumer` facade blocking-loop ownership is complete:
  `start()` now initializes scoped Effect consumers and returns after startup,
  while `stop()` closes the native consumer scope.
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
