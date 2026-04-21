---
layout: default
title: "Bootstrap Framework Technical Specification"
parent: "Tech Specs"
---

# Bootstrap Framework Technical Specification

## Overview

A generic, pluggable framework for running one-time initialisation steps
against a TrustGraph deployment — replacing the dedicated
`tg-init-trustgraph` container with a long-running processor that
converges the system to a desired initial state and then idles.

The framework is content-agnostic. It knows how to run, retry,
mark-as-done, and surface failures; the actual init work lives in
small pluggable classes called **initialisers**. Core initialisers
ship in the `trustgraph-flow` package; enterprise and third-party
initialisers can be loaded by dotted path without any core code
change.

## Motivation

The existing `tg-init-trustgraph` is a one-shot CLI run in its own
container. It performs two very different jobs (Pulsar topology
setup and config seeding) in a single script, is wasteful as a whole
container, cannot handle partial-success states, and has no way to
extend the boot process with enterprise-specific concerns (user
provisioning, workspace initialisation, IAM scaffolding) without
forking the tool.

A pluggable, long-running reconciler addresses all of this and slots
naturally into the existing processor-group model.

## Design

### Bootstrapper Processor

A single `AsyncProcessor` subclass. One entry in a processor group.
Parameters include the processor's own identity and a list of
**initialiser specifications** — each spec names a class (by dotted
path), a unique instance name, a flag string, and the parameters
that will be passed to the initialiser's constructor.

On each wake the bootstrapper does the following, in order:

1. Open a short-lived context (config client, flow-svc client,
   logger). The context is torn down at the end of the wake so
   steady-state idle cost is effectively nil.
2. Run all **pre-service initialisers** (those that opt out of the
   service gate — principally `PulsarTopology`, which must run
   before the services it gates on can even come up).
3. Check the **service gate**: cheap round-trips to config-svc and
   flow-svc. If either fails, skip to the sleep step using the
   short gate-retry cadence.
4. Run all **post-service initialisers** that haven't already
   completed at the currently-configured flag.
5. Sleep. Cadence adapts to state (see below).

### Initialiser Contract

An initialiser is a class with:

- A class-level `name` identifier, unique within the bootstrapper's
  configuration. This is the key under which completion state is
  stored.
- A class-level `wait_for_services` flag. When `True` (the default)
  the initialiser runs only after the service gate passes. When
  `False`, it runs before the gate, on every wake.
- A constructor that accepts the initialiser's own params as kwargs.
- An async `run(ctx, old_flag, new_flag)` method that performs the
  init work and returns on success. Any raised exception is
  logged and treated as a transient failure — the stored flag is
  not updated and the initialiser will re-run on the next cycle.

`old_flag` is the previously-stored flag string, or `None` if the
initialiser has never successfully run in this deployment. `new_flag`
is the flag the operator has configured for this run. This pair
lets an initialiser distinguish a clean first-run from a migration
between flag versions and behave accordingly (see "Flag change and
re-run safety" below).

### Context

The context is the bootstrapper-owned object passed to every
initialiser's `run()` method. Its fields are deliberately narrow:

| Field | Purpose |
|---|---|
| `logger` | A child logger named for the initialiser instance |
| `config` | A short-lived `ConfigClient` for config-svc reads/writes |
| `flow`   | A short-lived `RequestResponse` client for flow-svc |

The context is always fully-populated regardless of which services
a given initialiser uses, for symmetry. Additional fields may be
added in future without breaking existing initialisers. Clients are
started at the beginning of a wake cycle and stopped at the end.

Initialisers that need services beyond config-svc and flow-svc are
responsible for their own readiness checks and for raising cleanly
when a prerequisite is not met.

### Completion State

Per-initialiser completion state is stored in the reserved
`__system__` workspace, under a dedicated config type for bootstrap
state. The stored value is the flag string that was configured when
the initialiser last succeeded.

On each cycle, for each initialiser, the bootstrapper reads the
stored flag and compares it to the currently-configured flag. If
they match, the initialiser is skipped silently. If they differ,
the initialiser runs; on success, the stored flag is updated.

Because the state lives in a reserved (`_`-prefixed) workspace, it
is stored by config-svc but excluded from the config push broadcast.
Live processors never see it and cannot act on it.

### The Service Gate

The gate is a cheap, bootstrapper-internal check that config-svc
and flow-svc are both reachable and responsive. It is intentionally
a simple pair of low-cost round-trips — a config list against
`__system__` and a flow-svc `list-blueprints` — rather than any
deeper health check.

Its purpose is to avoid filling logs with noise and to concentrate
retry effort during the brief window when services are coming up.
The gate is applied only to initialisers with
`wait_for_services=True` (the default); `False` is reserved for
initialisers that set up infrastructure the gate itself depends on.

### Adaptive Cadence

The sleep between wake cycles is chosen from three tiers based on
observed state:

| Tier | Duration | When |
|---|---|---|
| Gate backoff | ~5 s | Services not responding — concentrate retry during startup |
| Init retry | ~15 s | Gate passes but at least one initialiser is not yet at its configured flag — transient failures, waiting on prereqs, recently-bumped flag not yet applied |
| Steady | ~300 s | All configured initialisers at their configured flag; gate passes; nothing to do |

The short tiers ensure a fresh deployment converges quickly;
steady state costs a single round-trip per initialiser every few
minutes.

### Failure Handling

An initialiser raising an exception does not stop the bootstrapper
or block other initialisers. Each initialiser in the cycle is
attempted independently; failures are logged and retried on the next
cycle. This means there is no ordered-DAG enforcement: order of
initialisers in the configuration determines the attempt order
within a cycle, but a dependency between two initialisers is
expressed by the dependant raising cleanly when its prerequisite
isn't satisfied. Over successive cycles the system converges.

### Flag Change and Re-run Safety

Each initialiser's completion state is a string flag chosen by the
operator. Typically these follow a simple version pattern
(`v1`, `v2`, ...), but the bootstrapper imposes no format.

Changing the flag in the group configuration causes the
corresponding initialiser to re-run on the next cycle. Initialisers
must be written so that re-running after a flag bump is safe — they
receive both the previous and the new flag and are responsible for
either cleanly re-applying the work or performing a step-change
migration from the prior state.

This gives operators an explicit, visible mechanism for triggering
re-initialisation. Re-runs are never implicit.

## Core Initialisers

The following initialisers ship in `trustgraph.bootstrap.initialisers`
and cover the base deployment case.

### PulsarTopology

Creates the Pulsar tenant and the four namespaces
(`flow`, `request`, `response`, `notify`) with appropriate
retention policies if they don't exist.

Opts out of the service gate (`wait_for_services = False`) because
config-svc and flow-svc cannot come online until the Pulsar
namespaces exist.

Parameters: Pulsar admin URL, tenant name.

Idempotent via the admin API (GET-then-PUT). Flag change causes
re-evaluation of all namespaces; any absent are created.

### TemplateSeed

Populates the reserved `__template__` workspace from an external
JSON seed file. The seed file has the standard shape of
`{config-type: {config-key: value}}`.

Runs post-gate. Parameters: path to the seed file, overwrite
policy (upsert-missing only, or overwrite-all).

On clean run, writes the whole file. On flag change, behaviour
depends on the overwrite policy — typically upsert-missing so
that operator-customised keys are preserved across seed-file
upgrades.

### WorkspaceInit

Creates a named workspace and populates it from the seed file or
from the full contents of the `__template__` workspace.

Runs post-gate. Parameters: workspace name, source (seed file or
`__template__`), optional `seed_file` path, `overwrite` flag.

When `source` is `template`, the initialiser copies every config
type and key present in `__template__` — there is no per-type
selection. Deployments that want to seed only a subset should
either curate the seed file they feed to `TemplateSeed` or use
`source: seed-file` directly here.

Raises cleanly if its source does not exist — depends on
`TemplateSeed` having run in the same cycle or a prior one.

### DefaultFlowStart

Starts a specific flow in a specific workspace using a specific
blueprint.

Runs post-gate. Parameters: workspace name, flow id, blueprint
name, description, optional parameter overrides.

Separated from `WorkspaceInit` deliberately so that deployments
which want a workspace without an auto-started flow can simply omit
this initialiser from their bootstrap configuration.

## Extensibility

New initialisers are added by:

1. Subclassing the initialiser base class.
2. Implementing `run(ctx, old_flag, new_flag)`.
3. Choosing `wait_for_services` (almost always `True`).
4. Adding an entry in the bootstrapper's configuration with the new
   class's dotted path.

No core code changes are required to add an enterprise or third-party
initialiser. Enterprise builds ship their own package with their own
initialiser classes (e.g. `CreateAdminUser`, `ProvisionWorkspaces`)
and reference them in the bootstrapper config alongside the core
initialisers.

## Reserved Workspaces

This specification relies on the "reserved workspace" convention:

- Any workspace id beginning with `_` is reserved.
- Reserved workspaces are stored normally by config-svc but never
  appear in the config push broadcast.
- Live processors cannot react to reserved-workspace state.

The bootstrapper uses two reserved workspaces:

- `__template__` — factory-default seed config, readable by
  initialisers that copy-from-template.
- `__system__` — bootstrapper completion state (under the
  `init-state` config type) and any other system-internal bookkeeping.

See the reserved-workspace convention in the config service for
the general rule and its enforcement.

## Non-Goals

- No DAG scheduling across initialisers. Dependencies are expressed
  by the dependant failing cleanly until its prerequisite is met,
  and convergence over subsequent cycles.
- No parallel execution of initialisers within a cycle. A cycle runs
  each initialiser sequentially.
- No implicit re-runs. Re-running an initialiser requires an explicit
  flag change by the operator.
- No cross-initialiser atomicity. Each initialiser's completion is
  recorded independently on its own success.

## Operational Notes

- Running the bootstrapper as a processor-group entry replaces the
  `tg-init-trustgraph` container. The script remains CLI-invocable
  for standalone testing (`Processor.launch(...)` pattern).
- First-boot convergence is typically a handful of short cycles
  followed by a transition to the steady cadence. Deployments
  should expect the first few minutes of logs to show
  initialisation activity, thereafter effective silence.
- Bumping a flag is a deliberate operational act. The log line
  emitted on re-run makes the event visible for audit.
