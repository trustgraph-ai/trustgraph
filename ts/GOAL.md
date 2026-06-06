# Goal Prompt

```text
/goal In `/home/elpresidank/YeeBois/dev/trustgraph/ts`, implement the Effect-native rewrite described in `EFFECT_NATIVE_REWRITE_PLAN.md`.

Follow the plan as the source of truth. The desired end state is that production TrustGraph APIs are Effect-first throughout backend/pubsub, messaging, processor/runtime, flow services, gateway, CLI, and service runners.

Hard constraints:
- Preserve existing features and wire behavior.
- Remove Promise-returning TrustGraph production APIs instead of keeping dual Promise/Effect methods.
- Remove production `Effect.runPromise` / `ManagedRuntime` compatibility bridges.
- Remove Fastify, `@fastify/websocket`, and Commander.
- Rebuild gateway surfaces with Effect v4 native `effect/unstable/httpapi`, `effect/unstable/http`, `effect/unstable/rpc`, and socket/platform layers.
- Rebuild CLI surfaces with `effect/unstable/cli`.
- Keep the existing native `effect/unstable/ai/McpServer` MCP rewrite; do not reintroduce server-side `@modelcontextprotocol/sdk` or `zod` in `packages/mcp`.
- Use `/home/elpresidank/YeeBois/projects/beep-effect/.repos/effect-v4` as the Effect v4 source reference.
- Preserve unrelated dirty work.

Work in staged gates:
1. Backend and NATS Effect API.
2. Messaging and processor API cleanup.
3. Flow service call-site migration.
4. Gateway HttpApi/RPC migration.
5. CLI/script migration.
6. Dependency cleanup and final verification.

Run the smallest relevant tests after each stage. Final done means all of these are green:
`bun run check:tsgo`
`bun run build`
`bun run lint`
`bun run test`
`bun run --cwd packages/mcp test`
`bun run workbench:qa`
`git diff --check`

Also verify no production Fastify/Commander use remains, and no production `Effect.runPromise`, `ManagedRuntime.make`, Promise API, or `async function main` remains in TrustGraph package/source surfaces except tests or unavoidable external type declarations.
```
