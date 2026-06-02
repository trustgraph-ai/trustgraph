# TrustGraph TS Native Class To Functional Effect Services Goal

Use the `grill-me` skill from:

`/home/elpresidank/YeeBois/projects/beep-effect/.agents/skills/grill-me/SKILL.md`

## Objective

Refactor the TrustGraph TypeScript port so production runtime code no longer
uses native TypeScript or JavaScript class syntax except where an Effect module
API truly requires class syntax and no practical functional form exists.

The preferred style is functional and pure:

- Functions, factories, closures, and object-literal service implementations.
- Functions returning functions or service objects instead of constructors.
- `Context.Service` tags plus `Layer` builders for dependency provision.
- `Effect.gen`, `Effect.fn`, `Effect.acquireRelease`, `Effect.addFinalizer`,
  and scoped Layers for lifecycle.
- Top-level `Effect.runPromise` only at CLI/bootstrap boundaries.

Terminal condition: repeated inventory agents find zero blocking native classes
in production runtime source like these current smells:

- `ts/packages/base/src/processor/async-processor.ts#L38-162`
- `ts/packages/base/src/processor/flow-processor.ts#L284-358`

## Class Policy

Blocking scope is production runtime source under `ts/packages/**/src`,
excluding `__tests__`, `*.test.ts`, and `*.spec.ts`.

Tests and scripts must still be inventoried separately, but they do not block
completion unless they are required to verify migrated production behavior.

Allowed class syntax is intentionally narrow and proof-based. Do not preserve
class syntax just because it is Effect-adjacent. For every candidate exemption,
prove that the specific Effect API requires class syntax and that a functional
alternative is not better.

Candidate exemptions to investigate, not blindly preserve:

- `S.Class`, `S.TaggedClass`, `S.TaggedErrorClass`, `S.ErrorClass`
- `Data.TaggedError`
- `Context.Service`
- Effect RPC / HTTP API class forms such as `Rpc.make` and `HttpApi.make`

If a functional Effect equivalent exists, use the functional form. The target
style is functions returning functions or service objects, not class-shaped
Effect code.

Blocking class forms include:

- Abstract base classes and inheritance-based processors.
- Service classes extending `AsyncProcessor`, `FlowProcessor`, or `LlmService`.
- Client API wrapper classes.
- Backend adapter classes.
- Spec/resource classes.
- Query/store/engine classes.
- Metrics/parser/lifecycle classes.
- React class components such as error boundaries.

## Required Workflow

1. Read and follow `grill-me`.
2. Before asking the user questions, use parallel read-only sub-agents to
   inventory class declarations.
3. Use AST-based inspection where possible; regex alone is not enough.
4. Split inventory agents by subsystem:
   - Base processor/messaging/runtime/specs/backend.
   - Flow service processors and LLM/embedding/RAG services.
   - Query/store engines and adapters.
   - Client socket/API wrappers.
   - Workbench production source.
5. Consolidate findings into:
   - Blocking production native classes.
   - Effect-native class forms with proof.
   - Functional replacements available for prior exemptions.
   - Non-blocking test/script classes.
6. Use `grill-me` to resolve any remaining API or rollout tradeoffs.
7. Produce a decision-complete implementation plan.
8. After approval, implement in phases and rerun inventory until blocking count
   is zero.

## Refactor Direction

Replace inheritance and mutable class instances with:

- Plain TypeScript service interfaces.
- `Context.Service` tags only where needed for Effect dependency injection.
- `Layer.succeed`, `Layer.effect`, and `Layer.scoped` for construction.
- Closure-held state only where necessary, preferably scoped and finalized.
- Object-literal services instead of class instances.
- Factory functions like `makeXService`, `makeXLayer`, and `runX`.
- `Effect.tryPromise` for external Promise APIs.
- `Effect.fn` for reusable effectful service methods.

Preserve behavior and in-repo call semantics, but do not preserve native class
constructors as public API. Replace exported classes with interfaces, service
tags, factory functions, or layer builders, and update all in-repo callers.

## Verification Requirements

Required gates:

- `cd ts && bun run check:tsgo`
- `cd ts && bun run build`
- `cd ts && bun run test`
- `cd ts && bun run workbench:qa`
- Add or provide an inventory command/script that fails on blocking production
  classes.
- Run the inventory command after every migration phase.
- Final inventory must report zero blocking production native classes.

Live smoke if service surfaces changed:

- `cd ts/deploy && docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build`
- `cd ts && bun run seed`
- `cd ts && bun run seed:demo`
- `cd ts && bun run seed:flows`
- `cd ts && SKIP_LLM=1 bun run test:pipeline`

## New Session Prompt

Paste this into a new Codex session:

```text
Use the grill-me skill from /home/elpresidank/YeeBois/projects/beep-effect/.agents/skills/grill-me/SKILL.md.

The repo is /home/elpresidank/YeeBois/dev/trustgraph and the TypeScript port is in ./ts. I want to remove native TypeScript/JavaScript class syntax from production runtime code and convert the port to functional, pure Effect services.

Before asking me questions, use parallel read-only sub-agents to inventory every class declaration under ts/packages/**/src. Production runtime source is the blocking scope; tests and scripts should be inventoried separately but are non-blocking. Use AST-based inspection where possible, not regex alone.

Allowed class syntax is extremely narrow and proof-based. Even Effect-native-looking classes such as S.Class, S.TaggedClass, S.TaggedErrorClass, S.ErrorClass, Data.TaggedError, Context.Service, Rpc.make, and HttpApi.make must be treated as candidate exemptions, not automatic exemptions. If a functional Effect equivalent exists, use the functional form. I prefer functions, factories, closures, object-literal service implementations, Context.Service tags, and Layers over all class-shaped code.

Use these files as representative smells:
- ts/packages/base/src/processor/async-processor.ts#L38-162
- ts/packages/base/src/processor/flow-processor.ts#L284-358

Inventory by subsystem: base processor/messaging/runtime/specs/backend; flow service processors and LLM/embedding/RAG services; query/store engines and adapters; client socket/API wrappers; workbench production source.

After inventory, use grill-me to resolve any remaining API or rollout tradeoffs, then produce a decision-complete implementation plan. After I approve the plan, implement in phases and repeat inventory until zero blocking production native classes remain.

Required verification: cd ts && bun run check:tsgo; cd ts && bun run build; cd ts && bun run test; cd ts && bun run workbench:qa; add or provide an inventory command/script that fails on blocking production classes. If service surfaces changed, also run the live docker/seed/pipeline smoke from this file.
```

## Goal Command

```text
/goal Use ts/CLASS_EFFECT_GOAL.md to run the TrustGraph TS native-class-to-functional-Effect-services migration. First use grill-me and parallel read-only sub-agents to inventory every native class declaration. Then produce and execute a decision-complete refactor plan that replaces classes with pure functions, factories, closures, object-literal services, Context.Service tags, and Layers. Terminal condition: repeated inventory agents and the repo inventory command report zero blocking native classes in production runtime source under ts/packages/**/src. Even Effect-native class forms such as S.Class, TaggedError classes, Context.Service, Rpc.make, and HttpApi.make must be treated as narrow proof-based exemptions; if a functional Effect equivalent exists, use it. Verify with check:tsgo, build, test, workbench:qa, and live smoke when service surfaces change. Preserve unrelated local files.
```
