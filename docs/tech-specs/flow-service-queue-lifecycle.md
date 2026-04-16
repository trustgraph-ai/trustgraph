---
layout: default
title: "Flow Service Separation and Queue Lifecycle Management"
parent: "Tech Specs"
---

# Flow Service Separation and Queue Lifecycle Management

## Overview

This specification describes the separation of the flow service from the
config service into an independent service, and the addition of explicit
queue lifecycle management to the pub/sub backend abstraction.

Every queue in the system has an explicit owner responsible for its
creation and deletion:

- **Flow and blueprint queues** — owned by the flow service
- **System queues** (config, librarian, knowledge, etc.) — owned by
  the services themselves

Consumers never create queues. They connect to queues that already
exist.

This addresses a fundamental problem across broker backends: without an
authoritative lifecycle owner, queues are created as a side effect of
consumer connections and never explicitly deleted. In RabbitMQ, this
leads to orphaned durable queues. In Pulsar, persistent topics and
subscriptions survive consumer crashes. In Kafka, topics persist
indefinitely. The solution is the same for all backends: explicit
lifecycle management through the `PubSubBackend` protocol.

---

## Background

### Current Architecture

The flow service (`FlowConfig`) and config service (`Configuration`)
are co-located in a single process: `trustgraph-flow/config/service`.
They share a `Processor` class that inherits from `AsyncProcessor` and
manages both config and flow request/response queues. `FlowConfig`
receives a direct reference to the `Configuration` object, giving it
backdoor access to `inc_version()` and `push()` — methods that bypass
the config service's own pub/sub interface.

The flow service manages flow lifecycle (start/stop) by manipulating
config state — active-flow entries, flow records, blueprint lookups —
but takes no active part in broker queue management. Queues are created
implicitly when the first consumer connects and are never explicitly
deleted.

### The Queue Lifecycle Problem

Queues are currently created as a side effect of consumer connections
(in `_connect()` for RabbitMQ, in `subscribe()` for Pulsar). No single
component owns queue lifecycle, leading to two failure modes:

- **Orphaned queues**: When a flow is stopped, consumers shut down but
  their queues remain — along with any messages in them. In RabbitMQ,
  durable queues persist indefinitely. In Pulsar, persistent topics and
  their subscriptions survive consumer disconnection unless
  `unsubscribe()` is explicitly called — which doesn't happen on crash
  or error paths.
- **Premature deletion**: If consumers attempt to delete queues on
  exit, error-path shutdowns destroy queues that other consumers or the
  system still need.

Neither strategy is reliable because neither the consumer nor the
broker knows whether a queue should exist — only the flow manager
knows that.

### Why Separation

The flow service currently piggybacks on the config service process.
Adding broker queue management to the flow service introduces operations
that may have significant latency — RabbitMQ queue operations are
generally fast, but Kafka topic creation can involve partition
assignment, replication, and leader election delays.

The config service is on the critical path for every service in the
system — all services read configuration on startup and respond to
config pushes. Blocking the config service's request/response loop
while waiting for broker operations risks cascading latency across the
entire deployment.

Separating the flow service into its own process gives it an
independent latency budget. A slow `start-flow` (waiting for queue
creation across multiple brokers) does not affect config reads.
Additionally, the flow service's direct access to the `Configuration`
object is a coupling that masks what should be a clean client
relationship — the flow service only needs to read and write config
entries, which is exactly what the existing config client provides.

---

## Design

### Queue Ownership Model

Every queue in the system has exactly one owner responsible for its
creation and deletion:

| Queue type | Owner | Created when | Deleted when |
|---|---|---|---|
| Flow queues | Flow service | `start-flow` | `stop-flow` |
| Blueprint queues | Flow service | `start-flow` (idempotent) | Never (shared across flow instances) |
| System queues (config, librarian, knowledge, etc.) | Each service | Service startup | Never (system lifetime) |

Consumers never create queues. The consumer's `_connect()` method
connects to a queue that must already exist — it does not declare or
create it.

### Flow Service as Independent Service

The flow service becomes its own `Processor(AsyncProcessor)` in a
separate module and process. It:

- Listens on the existing flow request/response queues (already distinct
  from config queues — no consumer migration needed).
- Uses the async `ConfigClient` (extending `RequestResponse`) to
  read/write config state (blueprints, active-flow entries, flow
  records). Config pushes are triggered automatically by config
  writes — the backdoor `inc_version()` and `push()` calls are no
  longer needed.
- Has direct access to the pub/sub backend (inherited from
  `AsyncProcessor`) for queue lifecycle operations.

The config service (`trustgraph-flow/config/service`) is simplified:
the flow consumer, flow producer, and `FlowConfig` class are removed.
It returns to being purely a config service.

### Queue Lifecycle in the Pub/Sub Backend

The `PubSubBackend` protocol gains queue management methods. All new
methods are async — backends that use blocking I/O (e.g., pika for
RabbitMQ) handle threading internally.

```
PubSubBackend:
    create_producer(...)              # existing
    create_consumer(...)              # existing
    close()                           # existing
    async create_queue(topic, subscription)    # new
    async delete_queue(topic, subscription)    # new
    async queue_exists(topic, subscription)    # new
    async ensure_queue(topic, subscription)    # new
```

- `create_queue` — create a queue. Idempotent if queue already exists
  with the same properties. Fails if properties mismatch.
- `delete_queue` — delete a queue and its messages. Idempotent if
  queue does not exist.
- `queue_exists` — check whether a queue exists. Returns bool.
- `ensure_queue` — create-if-not-exists convenience wrapper.

The `topic` and `subscription` parameters together identify the queue,
mirroring `create_consumer` where the queue name is derived from both.

Backend implementations:

- **RabbitMQ**: `queue_declare`, `queue_delete`, and
  `queue_declare(passive=True)` via pika. Blocking calls wrapped in
  `asyncio.to_thread` inside the backend. Queue name derived using the
  existing `_parse_queue_id` logic.
- **Pulsar**: REST calls to the Pulsar admin API (port 8080).
  Create/delete persistent topics, delete subscriptions. Requires admin
  URL as additional configuration alongside the broker URL.
- **Kafka** (future): `AdminClient.create_topics()` and
  `AdminClient.delete_topics()` from the `confluent-kafka` library.
  Uses the same bootstrap servers as the broker connection.

### Flow Start: Queue Creation

When `handle_start_flow` processes a flow start request, after
resolving parameters and computing the template-substituted topic
identifiers, it creates queues before writing config state.

Queues are created for both `cls["blueprint"]` and `cls["flow"]`
entries. Blueprint queue creation is idempotent — multiple flows
creating the same blueprint queue is safe.

The flow start request returns only after queues are confirmed ready.
This gives callers a hard guarantee: when `start-flow` succeeds, the
data path is fully wired.

### Flow Stop: Two-Phase Shutdown

Stopping a flow is a two-phase transaction with a retry window between
them.

**Phase 1 — Signal processors to shut down:**

1. Set the flow record's status to `"stopping"`. This marks the flow
   as in-progress so that if the flow service crashes mid-stop, it can
   identify and resume incomplete shutdowns on restart.
2. Remove the flow's variants from each processor's `active-flow`
   config entries.
3. Config push fires automatically. Each `FlowProcessor` receives the
   update, compares wanted vs current flows, and calls `stop_flow` on
   flows no longer wanted — closing consumers and producers.

**Phase 2 — Delete queues with retries, then finalise:**

1. Retry queue deletion with delays, giving processors time to react
   to the config change and disconnect. Queue deletion is idempotent —
   if a queue was already removed by a previous attempt or was never
   created, the operation succeeds silently. Only `cls["flow"]` entries
   (per-flow-instance queues) are deleted — `cls["blueprint"]` entries
   are shared infrastructure and are not touched.
2. Delete the `flow` record from config.

The flow service retries persistently. A queue that cannot be deleted
after retries is logged as an error but does not block the stop
transaction from completing — a leaked queue is less harmful than a
flow that cannot be stopped.

**Crash recovery:** On startup, the flow service scans for flow
records with `"status": "stopping"`. These represent incomplete
shutdowns from a previous run. For each, it resumes from the
appropriate point — if active-flow entries are already cleared, it
proceeds directly to phase 2 (queue deletion and flow record cleanup).

### System Service Queues

System services (config, librarian, knowledge, etc.) are not managed
by the flow service. Each service calls `ensure_queue` for its own
queues during startup. These queues persist for the lifetime of the
system and are never explicitly deleted.

### Consumer Connection

Consumers never create queues. The consumer connects to a queue that
must already exist — created either by the flow service (for flow and
blueprint queues) or by the service itself (for system queues).

For RabbitMQ, this means `_connect()` no longer calls `queue_declare`.
It connects to a queue by name and fails if the queue does not exist.

For Pulsar, `subscribe()` inherently creates a subscription. This is
how Pulsar works and does not conflict with the lifecycle model —
Pulsar's broker manages subscription state, and the flow service uses
the admin API for explicit cleanup.

---

## Operational Impact

### Deployment

The flow service is a new container/process alongside the existing
config service. It requires:

- Access to the message broker (same credentials as other services —
  inherited from `AsyncProcessor` via standard CLI args).
- Access to the config service via pub/sub (config request/response
  queues — same as any other service that reads config).
- For Pulsar: the admin API URL (separate from the broker URL).

It does not require direct Cassandra access.

### Backward Compatibility

- The flow request/response queue interface is unchanged — API gateway
  and CLI tools that send flow requests continue to work without
  modification.
- The config service loses its flow handling capability, so both
  services must be deployed together. This is a breaking change in
  deployment topology but not in API.
- Queue deletion on flow stop is new behaviour. Existing deployments
  that rely on queues persisting after flow stop (e.g. for post-mortem
  message inspection) would need to drain queues before stopping flows.

---

## Assumptions

- **The flow service is the sole writer of flow configuration.** The
  two-phase stop transaction relies on the flow record's `"stopping"`
  status being authoritative — no other service or process modifies
  flow records, active-flow entries, or flow blueprints. This is true
  today (only `FlowConfig` writes to these config keys) and must remain
  true after separation. The config service provides the storage, but
  the flow service owns the semantics.

---

## Design Decisions

| Decision | Resolution | Rationale |
|---|---|---|
| Queue ownership | Every queue has exactly one explicit owner | Eliminates implicit creation, makes lifecycle auditable |
| Queue deletion strategy | Retry persistently, don't block stop | A leaked queue is less harmful than a flow stuck in stopping state |
| Purge without delete | Not needed | Flows are fully dynamic — stop and restart recreates everything |
| Blueprint-level queues | Created on flow start (idempotent), never deleted | Shared across flow instances; creation is safe, deletion would break other flows |
| Flow stop atomicity | Two-phase with `"stopping"` state | Allows crash recovery; flow service can resume incomplete shutdowns |
| Backend protocol methods | All async | Backends hide blocking I/O internally; callers never deal with threading |
| Pulsar lifecycle | REST admin API, not no-op | Persistent topics and subscriptions survive crashes; explicit cleanup needed |
| Consumer queue creation | Consumers never create queues | Single ownership; `_connect()` connects to existing queues only |
