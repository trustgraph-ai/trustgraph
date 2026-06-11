# TrustGraph TS Effect-Native Status

## Current State

The TypeScript port on `ts-port-effect-v4` is Effect-first across the production
runtime surfaces completed in Phases 0-6. The law baseline is empty:
`scripts/effect-laws.allowlist.json` has no baseline entries and one documented
host-boundary exemption. The native-class inventory reports zero blocking
production native classes.

The client package's public barrel exports the Effect RPC gateway surface and
shared data models. The legacy `trustgraph-socket.ts` Promise `BaseApi` shim is
kept out of the package barrel and remains only for direct client tests.
Workbench QA uses its own minimal mock API shape.

## Adapted Effect Laws

- Data that crosses wires, persistence, or domain boundaries uses `S.Class`,
  `S.Struct`, or tagged schema unions. Service contracts and option bags may
  remain interfaces.
- Production code reads configuration through `Config`, not `process.env`.
- JSON encode/decode goes through Schema codecs such as
  `S.UnknownFromJsonString`.
- HTTP clients use `effect/unstable/http` with platform layers.
- Effects run at entrypoints through platform `runMain`; libraries return
  `Effect`, `Stream`, `Layer`, or service values.
- Deterministic ordering uses `effect/Array` and explicit `Order`s.
- File/path work uses platform services rather than `node:fs` or `node:path`.
- Errors owned by TrustGraph code use tagged errors on the Effect channel.

## Standing Exemptions

- `packages/workbench/src/main.tsx` may throw if `#root` is missing. This is a
  browser host boundary and the app cannot render without the mount point.
- `packages/flow/src/agent/mcp-tool/service.ts` may use the
  `@modelcontextprotocol/sdk` client behind Effect wrappers. Effect v4 provides
  server-side MCP support here, not a replacement client.
- Provider SDK integrations for OpenAI, Azure OpenAI, OpenAI-compatible,
  Mistral, and Ollama stay behind `Effect.tryPromise` and
  `makeLanguageModelProvider`. Claude already uses `@effect/ai-anthropic`.
- `PubSubBackend` remains a broker adapter contract. Effect `PubSub` is
  in-process only and is not a NATS replacement.
- Tests and QA fixtures are excluded from production law checks.

## Gate Commands

Phase 6 validation:

```sh
bun run check
bun run lint
bunx --bun turbo test build --force
git diff --check
```

Final Phase 7 acceptance, all no-cache where applicable:

```sh
bun run check:tsgo
bunx --bun turbo build lint test --force
bun run --cwd packages/mcp test
bun run workbench:qa
cd deploy && docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
bun run seed && bun run seed:flows && bun run seed:demo
SKIP_LLM=1 bun run test:pipeline
git diff --check
```

Final source audits:

```sh
bun scripts/check-effect-laws.ts
bun scripts/inventory-native-classes.ts
rg -n "fastify|@fastify/websocket|commander|zod" package.json packages scripts bun.lock
rg -n "@modelcontextprotocol/sdk" packages scripts package.json bun.lock
```

Expected result: no law baseline debt, zero blocking native classes, no Fastify,
Commander, Zod, or server-side MCP SDK reintroduction. The MCP SDK client
exemption remains documented above.
