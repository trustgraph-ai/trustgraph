# TrustGraph TS Effect-Native Rewrite Plan

## Summary

Bring the TypeScript port to a genuinely Effect-native shape while keeping existing TrustGraph capabilities working. The current native MCP rewrite should be preserved. The remaining work is to remove Promise-first TrustGraph APIs and replace manual host/framework plumbing with Effect v4-native backend, messaging, processor, HTTP/RPC, and CLI layers.

The implementation should proceed in green checkpoints rather than one broad sweep. Each stage should leave the repo closer to Effect-native and should run the smallest relevant gate before moving on.

## Non-Negotiable Architecture Decisions

- TrustGraph-authored production APIs should be Effect-first, not Promise-first.
- Remove exported Promise APIs from backend, messaging, processor, flow service, gateway, CLI, and service runner surfaces.
- Do not keep dual Promise and Effect methods on the same TrustGraph objects.
- Do not rely on Fastify, `@fastify/websocket`, Commander, or production `Effect.runPromise` / `ManagedRuntime` compatibility bridges.
- External JavaScript SDKs that are inherently Promise-based may be wrapped with `Effect.tryPromise`, but that Promise shape must stay behind Effect APIs.
- Gateway HTTP and WebSocket behavior should move to Effect v4 native modules: `effect/unstable/httpapi`, `effect/unstable/http`, `effect/unstable/rpc`, `effect/unstable/socket`, and platform Bun/Node HTTP/socket layers.
- CLI behavior should move to `effect/unstable/cli`.
- The MCP package should stay on the native `effect/unstable/ai/McpServer` implementation and must not reintroduce server-side `@modelcontextprotocol/sdk` or `zod`.

## Current Grounding

- `bun run check:tsgo` is green.
- `bun run build` is green.
- `bun run --cwd packages/mcp test` is green.
- `bun run test` currently fails only in `@trustgraph/base`, in `packages/base/src/__tests__/nats-backend.test.ts`.
- The NATS failures are a symptom of the backend still sitting between old Promise-shaped abstractions and newer JetStream calls. The rewrite should fix the contract, not only update the mock.
- The Effect v4 source of truth for APIs and examples is available at `/home/elpresidank/YeeBois/projects/beep-effect/.repos/effect-v4`.

## Stage 1: Backend And NATS

- Redefine `Message`, `BackendProducer`, `BackendConsumer`, and `PubSubBackend` around `Effect.Effect` return values.
- Make NATS connection, JetStream manager/client, stream initialization, and durable consumer handles scoped resources.
- Replace deprecated receive plumbing with modern JetStream consumer APIs.
- Preserve behavior for stream creation, durable consumer creation, headers, JSON/schema encode/decode, receive timeout returning `null`, ack/nak, close/drain, and tagged `PubSubError` mapping.
- Update NATS tests and in-memory fake backends to the new Effect-native interface.

Verification:

- `bun run --cwd packages/base test src/__tests__/nats-backend.test.ts`
- `bun run --cwd packages/base test`
- `bun run check:tsgo`

## Stage 2: Messaging And Processor Runtime

- Remove Promise facades from `makeProducer`, `makeConsumer`, `makeRequestResponse`, processor `start` / `stop` / `run`, and flow compatibility wrappers.
- Expose Effect values, scoped constructors, Context services, Layers, and finalizers as the only TrustGraph API shape.
- Convert message handlers, config handlers, shutdown callbacks, producer send/flush/close, consumer receive/ack/nak/close, and request/response operations to Effect functions.
- Remove internal `ManagedRuntime.make(Layer.empty)` compatibility runtimes from production source.

Verification:

- `bun run --cwd packages/base test`
- `bun run check:tsgo`

## Stage 3: Flow Service Call Sites

- Convert flow service state methods that currently call `Effect.runPromise` into Effect-valued service methods.
- Keep public feature behavior unchanged for config, flow manager, librarian, knowledge cores, retrieval, embeddings, triples, agent, MCP tool, and text-completion services.
- Convert test fakes to the same Effect-native backend/messaging contracts.

Verification:

- `bun run --cwd packages/flow test`
- `bun run test`
- `bun run check:tsgo`

## Stage 4: Gateway HTTP And RPC

- Remove Fastify and `@fastify/websocket` from `packages/flow`.
- Rebuild the gateway with Effect v4 `HttpApi` groups/endpoints and native RPC/socket layers.
- Preserve existing behavior:
  - `POST /api/v1/workbench/dispatch`
  - `POST /api/v1/:kind`
  - `POST /api/v1/flow/:flow/service/:kind`
  - `POST /api/v1/flow/:flow/load`
  - `GET /api/v1/rpc`
  - `GET /api/v1/metrics`
  - bearer auth behavior and RPC token behavior
  - existing response/error shapes expected by clients and workbench
- Use native Effect HTTP test utilities or route-level protocol tests instead of Fastify injection.

Verification:

- `bun run --cwd packages/flow test`
- `bun run --cwd packages/client test`
- `bun run test`
- `bun run build`

## Stage 5: CLI And Runner Scripts

- Remove Commander from `packages/cli`.
- Rebuild CLI commands with `effect/unstable/cli` and Effect-native socket/API clients.
- Convert service runner scripts to launch Effect programs directly with platform runtime `runMain` style execution.
- Remove `run(): Promise<void>` exports from flow services; export Effect programs/layers and Effect-native `runMain` helpers instead.
- Leave script-only demo/seed tools as follow-up only if they are outside production package source, but do not let production packages depend on Promise facades.

Verification:

- `bun run --cwd packages/cli test`
- `bun run check:tsgo`
- `bun run build`
- `bun run test`

## Stage 6: Cleanup And Acceptance

- Remove obsolete dependencies from package manifests and lockfile:
  - `fastify`
  - `@fastify/websocket`
  - `commander`
  - any legacy dependency made unnecessary by the rewrite
- Preserve unrelated dirty work. Do not revert user changes.
- Use parallel agents for bounded audits or disjoint rewrite slices when useful.
- Use Graphiti memory if available; if unavailable, continue safely and report it skipped.

Final verification:

- `bun run check:tsgo`
- `bun run build`
- `bun run lint`
- `bun run test`
- `bun run --cwd packages/mcp test`
- `bun run workbench:qa` after installing the matching Playwright browser if needed
- `git diff --check`
- `rg -n "fastify|@fastify/websocket|commander" packages package.json bun.lock` has no production dependency/use hits
- `rg -n "Effect\\.runPromise|ManagedRuntime\\.make|Promise<|async function main" packages/base/src packages/flow/src packages/cli/src scripts -g "*.ts"` has no production-source hits except tests or unavoidable external type declarations that are not TrustGraph APIs

Do not mark the goal complete until all required gates are green, or until a real external blocker is reported with the exact failing command, error, and smallest next action.
