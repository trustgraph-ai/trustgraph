---
layout: default
title: "Workspace-Scoped Services"
parent: "Tech Specs"
---

# Workspace-Scoped Services

## Problem Statement

Workspace-scoped services (librarian, config, knowledge, collection
management) currently operate on global queues — a single
`request:tg:librarian` queue handles requests for all workspaces.
Workspace identity is carried as a field in the request body, set by
the gateway after authentication.  This creates several problems:

- **No structural isolation.**  All workspaces share a single queue.
  Workspace scoping depends entirely on a body field being populated
  correctly.  If the field is missing or wrong, the service operates
  on the wrong workspace — or fails with a confusing error.  This is
  a security concern: workspace isolation should be enforced by
  infrastructure, not by trusting a field.

- **Redundant workspace fields.**  Nested objects within requests
  (e.g. `processing-metadata`, `document-metadata`) carry their own
  `workspace` fields alongside the top-level request workspace.
  The gateway resolves the top-level workspace but does not
  propagate into nested payloads.  Services that read workspace from
  a nested object instead of the top-level address see `None` and
  fail.

- **No workspace lifecycle awareness.**  Workspace-scoped services
  have no mechanism to learn when workspaces are created or deleted.
  Flow processors discover workspaces indirectly through config
  entries, but workspace-scoped services on global queues have no
  equivalent.  There is no event when a workspace appears or
  disappears.

- **Inconsistency with flow-scoped services.**  Flow-scoped services
  already use per-workspace, per-flow queue names
  (`request:tg:{workspace}:embeddings:{class}`).  Workspace-scoped
  services are the exception — they sit on global queues while
  everything else is structurally isolated.

## Design

### Per-workspace queues for workspace-scoped services

Workspace-scoped services move from global queues to per-workspace
queues.  The queue name includes the workspace identifier:

**Current (global):**
```
request:tg:librarian
request:tg:config
```

**Proposed (per-workspace):**
```
request:tg:librarian:{workspace}
request:tg:config:{workspace}
```

The gateway routes requests to the correct queue based on the
resolved workspace from authentication — the same workspace that
today gets written into the request body.  The workspace is now part
of the queue address, not just a field in the payload.

Services subscribe to per-workspace queues.  When a new workspace is
created, they subscribe to its queue.  When a workspace is deleted,
they unsubscribe.

### Workspace lifecycle via the `__workspaces__` config namespace

Workspace lifecycle events are modelled as config changes in a
reserved `__workspaces__` namespace.  This mirrors the existing
`__system__` namespace — a reserved space for infrastructure
concerns that don't belong to any user workspace.

When IAM creates a workspace, it writes an entry to the config
service:

```
workspace: __workspaces__
type: workspace
key: <workspace-id>
value: {"enabled": true}
```

When IAM deletes (or disables) a workspace, it updates or deletes
the entry.  The config service sees this as a normal config change
and pushes a notification through the existing `ConfigPush`
mechanism.

This avoids introducing a new notification channel.  The config
service already has the machinery to notify subscribers of changes
by type and workspace.  Workspace lifecycle is just another config
type that services can register handlers for.

### Config push changes

#### Remove `_`-prefix suppression

The config service currently suppresses notifications for workspaces
whose names start with `_`.  This suppression is removed — the
config service pushes notifications for all workspaces
unconditionally.

The filtering moves to the consumer side.  `AsyncProcessor` already
filters `_`-prefixed workspaces in its config handler dispatch
(lines 212 and 315 of `async_processor.py`).  This filtering is
retained as the default behaviour, but handlers can opt in to
infrastructure namespaces by registering for them explicitly (see
`WorkspaceProcessor` below).

#### Workspace change events

The `ConfigPush` message gains a `workspace_changes` field alongside
the existing `changes` field:

```python
@dataclass
class ConfigPush:
    version: int = 0

    # Config changes: type -> [affected workspaces]
    changes: dict[str, list[str]] = field(default_factory=dict)

    # Workspace lifecycle: created/deleted workspace lists
    workspace_changes: WorkspaceChanges | None = None

@dataclass
class WorkspaceChanges:
    created: list[str] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)
```

The config service populates `workspace_changes` when it detects
changes to the `__workspaces__` config namespace.  A new key
appearing is a creation; a key being deleted is a deletion.

Services that don't care about workspace lifecycle ignore the field.
Services that do (workspace-scoped services, the gateway) react by
subscribing to or tearing down per-workspace queues.

### The `WorkspaceProcessor` base class

A new base class sits between `AsyncProcessor` and `FlowProcessor`
in the processor hierarchy:

```
AsyncProcessor → WorkspaceProcessor → FlowProcessor
```

`WorkspaceProcessor` manages per-workspace queue lifecycle the same
way `FlowProcessor` manages per-flow lifecycle.  It:

1. On startup, discovers existing workspaces by fetching config from
   the `__workspaces__` namespace (using the existing
   `_fetch_type_all_workspaces` pattern).

2. For each workspace, subscribes to the service's per-workspace
   queue (e.g. `request:tg:librarian:{workspace}`).

3. Registers a config handler for the `workspace` type in the
   `__workspaces__` namespace.  When a workspace is created, it
   subscribes to the new queue.  When a workspace is deleted, it
   unsubscribes and tears down.

4. Exposes hooks for derived classes:
   - `on_workspace_created(workspace)` — called after subscribing
     to the new workspace's queue.
   - `on_workspace_deleted(workspace)` — called before
     unsubscribing from the workspace's queue.

`FlowProcessor` extends `WorkspaceProcessor` instead of
`AsyncProcessor`.  Flows exist within workspaces, so the hierarchy
is natural: workspace creation triggers queue subscription, then
flow config changes within that workspace trigger flow start/stop.

Services that are workspace-scoped but not flow-scoped (librarian,
knowledge, collection management) extend `WorkspaceProcessor`
directly.

### Gateway routing changes

The gateway currently dispatches workspace-scoped requests to global
service dispatchers.  This changes to per-workspace dispatchers that
route to per-workspace queues.

For HTTP requests, the resolved workspace from the URL path
(`/api/v1/workspaces/{w}/library`) determines the target queue.

For WebSocket requests via the Mux, the resolved workspace from
`enforce_workspace` determines the target queue.  The Mux already
resolves workspace before dispatching (line 214 of `mux.py`); the
change is that `invoke_global_service` uses workspace to select the
queue, rather than routing to a single global queue.

System-level services (IAM) remain on global queues — they are not
workspace-scoped.

### Workspace field on nested metadata objects

With per-workspace queues, the workspace is part of the queue
address.  Services know which workspace they are serving by which
queue a message arrived on.

The `workspace` field on `DocumentMetadata` and
`ProcessingMetadata` in the librarian schema becomes a storage
attribute — the workspace the record belongs to, populated by the
service from the request context, not by the caller.  The service
reads workspace from `request.workspace` (the resolved address) or
from the queue context, never from a nested payload field.

Callers are not required to populate workspace on nested objects.
The service fills it in authoritatively from the request context
before storing.

## Interaction with existing specs

### IAM (`iam.md`, `iam-contract.md`)

IAM is the authority for workspace existence.  When IAM creates or
deletes a workspace, it writes to the `__workspaces__` config
namespace.  This is a two-step operation: register the workspace in
IAM's own store (`iam_workspaces` table), then announce it via
config.

The IAM service itself remains on a global queue — it is a
system-level service, not workspace-scoped.

### Config service

The config service is workspace-scoped — it stores per-workspace
configuration.  Under this design, the config service moves to
per-workspace queues like other workspace-scoped services.

On startup, the config service discovers workspaces from its own
store (it has direct access to the config tables, unlike other
services that fetch via request/response).  It subscribes to
per-workspace queues for each known workspace.

When IAM writes a new workspace entry to the `__workspaces__`
namespace, the config service sees the write directly (it is the
config service), creates the per-workspace queue, and pushes the
notification.

### Flow blueprints (`flow-blueprint-definition.md`)

Flow blueprints already use `{workspace}` in queue name templates.
No changes needed — flows are created within an already-existing
workspace, so the per-workspace infrastructure is in place before
flow start.

### Data ownership (`data-ownership-model.md`)

This spec reinforces the data ownership model: a workspace is the
primary isolation boundary, and per-workspace queues make that
boundary structural rather than conventional.

## Migration

### Queue naming

Existing deployments use global queues for workspace-scoped
services.  Migration requires:

1. Deploy updated services that subscribe to both global and
   per-workspace queues during a transition period.
2. Update the gateway to route to per-workspace queues.
3. Drain the global queues.
4. Remove global queue subscriptions from services.

### `__workspaces__` bootstrap

On first start after migration, IAM populates the `__workspaces__`
config namespace with entries for all existing workspaces from
`iam_workspaces`.  This seeds the config store so that
workspace-scoped services discover existing workspaces on startup.

### Config push compatibility

The `workspace_changes` field on `ConfigPush` is additive.
Services that don't understand it ignore it (the field defaults to
`None`).  No breaking change to the push protocol.

## Summary of changes

| Component | Change |
|-----------|--------|
| Queue names | Workspace-scoped services move from `request:tg:{service}` to `request:tg:{service}:{workspace}` |
| `__workspaces__` namespace | New reserved config namespace for workspace lifecycle |
| IAM service | Writes to `__workspaces__` on workspace create/delete |
| Config service | Removes `_`-prefix notification suppression; generates `workspace_changes` events; moves to per-workspace queues |
| `ConfigPush` schema | Adds `workspace_changes` field (`WorkspaceChanges` dataclass) |
| `WorkspaceProcessor` | New base class managing per-workspace queue lifecycle |
| `FlowProcessor` | Extends `WorkspaceProcessor` instead of `AsyncProcessor` |
| `AsyncProcessor` | Relaxes `_`-prefix filtering to allow opt-in for infrastructure namespaces |
| Gateway | Routes workspace-scoped requests to per-workspace queues |
| Librarian schema | `workspace` on nested metadata becomes a service-populated storage attribute, not a caller-supplied address |

## Implementation Plan

### Phase 1: Foundation — `__workspaces__` namespace and config push

- **`ConfigPush` schema** (`trustgraph-base/trustgraph/schema/services/config.py`): Add `WorkspaceChanges` dataclass and `workspace_changes` field.
- **Config push serialization** (`trustgraph-base/trustgraph/messaging/translators/`): Encode/decode the new field.
- **Config service** (`trustgraph-flow/trustgraph/config/`): Detect writes to `__workspaces__` namespace and populate `workspace_changes` on the push message. Remove `_`-prefix notification suppression.
- **`AsyncProcessor`** (`trustgraph-base/trustgraph/base/async_processor.py`): Relax `_`-prefix filtering so handlers can opt in to infrastructure namespaces.
- **IAM service** (`trustgraph-flow/trustgraph/iam/`): Write to `__workspaces__` config namespace on `create-workspace` and `delete-workspace`. Add bootstrap step to seed `__workspaces__` entries for existing workspaces.

### Phase 2: `WorkspaceProcessor` base class

- **New `WorkspaceProcessor`** (`trustgraph-base/trustgraph/base/workspace_processor.py`): Implements workspace discovery on startup, per-workspace queue subscribe/unsubscribe, workspace lifecycle handler registration, `on_workspace_created`/`on_workspace_deleted` hooks.
- **`FlowProcessor`** (`trustgraph-base/trustgraph/base/flow_processor.py`): Re-parent from `AsyncProcessor` to `WorkspaceProcessor`.
- **Verify** existing flow processors continue to work — the new layer should be transparent to them.

### Phase 3: Per-workspace queues for workspace-scoped services

- **Queue definitions** (`trustgraph-base/trustgraph/schema/`): Update queue names for librarian, config, knowledge, collection management to include `{workspace}`.
- **Librarian** (`trustgraph-flow/trustgraph/librarian/`): Extend `WorkspaceProcessor`. Remove reliance on workspace from nested metadata objects.
- **Knowledge service, collection management** and other workspace-scoped services: Extend `WorkspaceProcessor`.
- **Config service**: Self-bootstrap per-workspace queues from its own store on startup; subscribe to new workspace queues when `__workspaces__` entries appear.

### Phase 4: Gateway routing

- **Gateway dispatcher manager** (`trustgraph-flow/trustgraph/gateway/dispatch/manager.py`): Route workspace-scoped services to per-workspace queues using resolved workspace. System-level services (IAM) remain on global queues.
- **Mux** (`trustgraph-flow/trustgraph/gateway/dispatch/mux.py`): Pass workspace to `invoke_global_service` for workspace-scoped services.
- **HTTP endpoints** (`trustgraph-flow/trustgraph/gateway/endpoint/`): Route to per-workspace queues based on URL path workspace.

### Phase 5: Schema cleanup

- **`DocumentMetadata`, `ProcessingMetadata`** (`trustgraph-base/trustgraph/schema/services/library.py`): Remove `workspace` field from nested metadata objects, or retain as a service-populated storage attribute only.
- **Serialization** (`trustgraph-flow/trustgraph/gateway/dispatch/serialize.py`, `trustgraph-base/trustgraph/messaging/translators/metadata.py`): Update translators to match.
- **API client** (`trustgraph-base/trustgraph/api/library.py`): Stop sending workspace in nested payloads.
- **Librarian service** (`trustgraph-flow/trustgraph/librarian/`): Populate workspace on stored records from request context.

### Dependencies

```
Phase 1 (foundation)
  ↓
Phase 2 (WorkspaceProcessor)
  ↓
Phase 3 (per-workspace queues) ←→ Phase 4 (gateway routing)
  ↓                                   ↓
           Phase 5 (schema cleanup)
```

Phases 3 and 4 can be developed in parallel but must be deployed together — services expecting per-workspace queues need the gateway to route to them.

## References

- [Identity and Access Management](iam.md) — workspace registry,
  authentication, and workspace resolution.
- [IAM Contract](iam-contract.md) — resource model and workspace as
  address vs. parameter.
- [Data Ownership and Information Separation](data-ownership-model.md)
  — workspace as isolation boundary.
- [Config Push and Poke](config-push-poke.md) — config notification
  mechanism.
- [Flow Blueprint Definition](flow-blueprint-definition.md) —
  `{workspace}` template variable in queue names.
- [Flow Service Queue Lifecycle](flow-service-queue-lifecycle.md) —
  queue ownership and lifecycle model.
