# TrustGraph Effect-Native Rewrite Playbook

This playbook is the context packet for read-only sub-agents that audit the
TrustGraph TypeScript port for code that hand-rolls behavior already provided by
Effect v4. It is not an implementation plan for a single rewrite. Its job is to
make future scouts fast, grounded, and allergic to invented APIs.

## Source Baseline

Verify these paths at the start of every audit run:

- TrustGraph TS port: `/home/elpresidank/YeeBois/dev/trustgraph/ts`
- Effect v4 subtree: `/home/elpresidank/YeeBois/projects/beep-effect2/.repos/effect-v4`
- Installed Effect fallback: `ts/node_modules/effect`
- Installed Atom React fallback: `ts/packages/workbench/node_modules/@effect/atom-react`

The prompt typo path `~/YeeBois/projecects/...` is not valid on this machine.
Use `~/YeeBois/projects/...`.

When a package is not present in the subtree, verify it from TrustGraph's
installed package sources before proposing a replacement. This matters for
`effect/unstable/reactivity`, `effect/unstable/ai`, `effect/unstable/rpc`,
`effect/unstable/socket`, `effect/unstable/http`, `effect/unstable/httpapi`,
and `@effect/atom-react`.

Important import rule: the Effect v4 subtree contains separate packages such as
`@effect/ai`, `@effect/rpc`, and `@effect/platform`, but TrustGraph currently
resolves many beta APIs through `effect/unstable/*` import paths. Prefer the
installed TrustGraph import path when it exists; use the subtree package path as
source proof, not as an automatic import recommendation.

## Primitive Map

Use this map as the starting baseline. A finding is only valid when it cites the
TrustGraph path, the import path, and the Effect source path that proves the
primitive exists.

| Handrolled pattern | Preferred Effect primitive | Import path | Verified source |
| --- | --- | --- | --- |
| Promise loops, top-level async orchestration | `Effect`, `Effect.fn`, `Effect.scoped`, `Effect.runPromiseWith` at boundaries | `effect` | `packages/effect/src/Effect.ts` |
| Resource construction and teardown | `Layer`, `Scope`, `Effect.acquireRelease`, `Effect.addFinalizer` | `effect` | `packages/effect/src/Layer.ts`, `packages/effect/src/Scope.ts` |
| Mutable service state | `Ref`, `SynchronizedRef`, `SubscriptionRef` | `effect` | `packages/effect/src/Ref.ts`, `packages/effect/src/SynchronizedRef.ts` |
| Polling, delays, retry/backoff | `Schedule`, `Effect.sleep`, `Effect.retry` | `effect` | `packages/effect/src/Schedule.ts`, `packages/effect/src/Effect.ts` |
| Callback queues and streaming fanout | `Queue`, `PubSub`, `Stream`, `Channel` | `effect` | `packages/effect/src/Queue.ts`, `packages/effect/src/PubSub.ts`, `packages/effect/src/Stream.ts`, `packages/effect/src/Channel.ts` |
| Env/config decoding | `Config`, `ConfigProvider`, platform config providers | `effect`, `effect/ConfigProvider`, provider packages | `packages/effect/src/Config.ts`, `packages/effect/src/ConfigProvider.ts`, `packages/platform/src/PlatformConfigProvider.ts` |
| JSON/wire schemas | `Schema`, `ParseResult`, `RpcSchema` | `effect/Schema`, `effect/unstable/rpc/RpcSchema` | `packages/effect/src/Schema.ts`, `ts/node_modules/effect/src/unstable/rpc/RpcSchema.ts` |
| WebSocket lifecycle and framing | `Socket`, `RpcClient`, `RpcServer`, `RpcSerialization` | `effect/unstable/socket`, `effect/unstable/rpc` | `ts/node_modules/effect/src/unstable/socket/*.ts`, `ts/node_modules/effect/src/unstable/rpc/*.ts` |
| HTTP servers/clients and typed APIs | `HttpApi`, `HttpApiClient`, `HttpApiBuilder`, `HttpClient`, `HttpServer` | `effect/unstable/http`, `effect/unstable/httpapi`, platform providers | `ts/node_modules/effect/src/unstable/http/*.ts`, `ts/node_modules/effect/src/unstable/httpapi/*.ts` |
| File, storage, and process IO | `FileSystem`, `KeyValueStore`, `ChildProcess`, `ChildProcessSpawner` | `effect/FileSystem`, `effect/unstable/persistence/KeyValueStore`, `effect/unstable/process/*`, provider packages | `ts/node_modules/effect/src/FileSystem.ts`, `ts/node_modules/effect/src/unstable/persistence/KeyValueStore.ts`, `ts/node_modules/effect/src/unstable/process/*.ts` |
| Browser local storage and clipboard | `BrowserKeyValueStore`, `Clipboard`, `BrowserHttpClient`, `BrowserSocket` | `@effect/platform-browser/*` | `ts/node_modules/.bun/@effect+platform-browser@4.0.0-beta.75+a5c1409dbf4ddafe/node_modules/@effect/platform-browser/src/*.ts` |
| AI tools, MCP, and model calls | `Tool`, `Toolkit`, `McpServer`, `McpSchema`, `LanguageModel`, provider layers | `effect/unstable/ai`, provider packages such as `@effect/ai-openai` | `ts/node_modules/effect/src/unstable/ai/*.ts`, `packages/ai/ai/src/*.ts` |
| Workbench async state | `Atom`, `AtomRpc`, `AtomHttpApi`, `AsyncResult`, `AtomRegistry`, `Reactivity` | `effect/unstable/reactivity`, `@effect/atom-react` | `ts/node_modules/effect/src/unstable/reactivity/*.ts`, `ts/packages/workbench/node_modules/@effect/atom-react/src/*.ts` |
| Metrics and logs | `Metric`, `Logger`, `Effect.log*` | `effect`, `@effect/opentelemetry` | `packages/effect/src/Metric.ts`, `packages/effect/src/Logger.ts` |

Known concrete exports useful to scouts:

- `Socket.makeWebSocket`, `Socket.fromWebSocket`, `Socket.toChannel`,
  `Socket.toChannelString`, `Socket.layerWebSocket`.
- `RpcClient.layerProtocolSocket`, `RpcServer.layerProtocolWebsocket`,
  `RpcServer.layerProtocolSocketServer`, `RpcSerialization.layerNdjson`,
  `RpcSerialization.layerNdJsonRpc`.
- `BunFileSystem`, `BunSocket`, `BunHttpClient`, `BunHttpServer`,
  `BunRuntime`, `BunChildProcessSpawner` from `@effect/platform-bun`.
- `BrowserKeyValueStore.layerLocalStorage`,
  `BrowserKeyValueStore.layerSessionStorage`,
  `BrowserHttpClient.layerXMLHttpRequest`.
- `Atom.make`, `Atom.runtime`, `Atom.fn`, `Atom.family`,
  `Atom.subscriptionRef`, `AtomRegistry.layer`, `Reactivity.layer`,
  `Reactivity.query`, `Reactivity.stream`, `Reactivity.mutation`.
- `Tool.make`, `Toolkit.make`, `McpServer.registerToolkit`,
  `LanguageModel.generateText`, `LanguageModel.streamText`.

## Scout Workflow

1. Confirm repo state with `git status -sb`. Preserve unrelated files,
   especially `.idea/effect.intellij.xml`.
2. Refresh the source baseline above. If a path moved, record the corrected path
   in the report before making any recommendations.
3. Run quick signal scans:

   ```sh
   rg -n "new Promise|setTimeout|while \\(|receive\\(|Effect\\.runPromise|toPromiseRequestor|makeAsyncProcessor|process\\.env|JSON\\.parse|JSON\\.stringify|localStorage|new Map|WebSocket" ts/packages --glob '*.ts' --glob '*.tsx'
   ```

4. Split scouts by lane. If the thread cannot spawn every scout in parallel,
   run them in batches using the same report schema.
5. Every finding must include both:
   - Evidence of the handrolled TrustGraph pattern.
   - Evidence of the exact Effect primitive that could replace it.
6. Do not rewrite code in this audit. The output is a ranked opportunity map and
   a recommended PR order.

## Agent Lanes

Use these lane prompts as the durable starting point.

### Base Messaging And Processor Runtime

Inspect `ts/packages/base/src/messaging`, `ts/packages/base/src/processor`, and
`ts/packages/base/src/spec`. Find Promise compatibility facades, polling
receivers, manual request/response caches, top-level `Effect.runPromise`, and
mutable maps. Compare against `Queue`, `PubSub`, `Stream`, `Scope`, `Layer`,
`Schedule`, `Ref`, and `SynchronizedRef`.

### Flow Stateful Services

Inspect `ts/packages/flow/src/config`, `librarian`, `cores`, `flow-manager`,
`prompt`, and service entrypoints. Find `makeAsyncProcessor` object services,
`while (this.running)`, `sleep`, `receive(2000)`, local persistence, and
process-env config. Compare against scoped layers, state refs, schedules,
`FileSystem`, `KeyValueStore`, `Config`, and schema codecs. In TrustGraph's
installed beta, prefer `effect/FileSystem` and
`effect/unstable/persistence/KeyValueStore` plus runtime-specific provider
packages.

### Gateway And RPC Boundaries

Inspect `ts/packages/flow/src/gateway` and `ts/packages/client/src/socket`.
Find manual requestor caches, streaming completion detectors, WebSocket
constructor shims, Promise-returning compatibility APIs, and repeated
`Effect.runPromise`. Compare against `Socket`, `RpcClient`, `RpcServer`,
`RpcSerialization`, `Stream`, `Queue`, and `Scope`.

### RAG, Agent, Provider, And Storage Layers

Inspect `ts/packages/flow/src/retrieval`, `agent`, `storage`, `query`, `model`,
and `embeddings`. Find `toPromiseRequestor`, direct SDK resource management,
ambient config, JSON parsing, and manual telemetry. Compare against
`EffectRequestResponse`, `Stream`, provider `Layer`s, `Config`, `Schema`,
`Metric`, `Logger`, and `effect/unstable/ai`.

### MCP And Workbench

Inspect `ts/packages/mcp` and `ts/packages/workbench`. Treat these as
lower-priority unless a handrolled pattern clearly remains. Prefer making the
Effect MCP server canonical over rewriting it from scratch. In workbench,
compare local storage and remote state wiring against `BrowserKeyValueStore`,
`AtomRpc`, `AtomHttpApi`, `AsyncResult`, and `Reactivity`.

## Report Schema

Each scout must return findings in this shape:

```md
## Finding: <short title>

- Priority: P0 | P1 | P2 | No-op
- Impact: 1-5
- Risk: 1-5
- Confidence: 1-5
- TrustGraph evidence: <path:line> and pattern name
- Effect evidence: <import path> and source path
- Current behavior: <what must be preserved>
- Rewrite shape: <Effect-native replacement direction>
- Tests: <specific existing or required tests>
- Blockers: <unknowns, API constraints, compatibility requirements>
```

Scoring:

- P0: large handrolled lifecycle/concurrency/transport surface with a verified
  Effect primitive and clear behavior-preserving route.
- P1: real replacement opportunity, but either risk or compatibility needs a
  focused design pass.
- P2: cleanup or local modernization; useful but not strategic.
- No-op: current code is already Effect-native, public-boundary Promise code is
  intentional, or the Effect primitive does not actually fit.

## Acceptance Checks

For an audit-only pass:

```sh
git status -sb
git diff --check -- ts/EFFECT_NATIVE_REWRITE_PLAYBOOK.md ts/EFFECT_NATIVE_REWRITE_AUDIT.md
```

For any later implementation PR, rerun the relevant package tests and at least:

```sh
cd ts && bun run check:tsgo
cd ts && bun run build
cd ts && bun run test
```

If gateway, live services, or workbench behavior changes, also run the existing
smoke lanes from `ts/CLASS_EFFECT_GOAL.md`.
