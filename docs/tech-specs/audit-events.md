---
layout: default
title: "Audit Events Technical Specification"
parent: "Tech Specs"
---

# Audit Events Technical Specification

## Overview

This specification defines the audit event system for TrustGraph.
Audit events provide a structured, complete record of security-
relevant operations: API gateway invocations and IAM decisions.

The design principle is: **emit everything, let consumers decide.**
Audit events are cheap to produce (a pub/sub message per operation)
and rich enough to support any downstream consumer — compliance
dashboards, SIEM integration, anomaly detection, billing metering,
or simple grep-based debugging.  This spec covers event production
only.  Storage, retention, alerting, and presentation are
deployment-specific concerns handled by consumers outside this
boundary.

## Motivation

TrustGraph currently has operational logging (Python `logging` to
stdout/Loki) but no structured audit trail.  Operational logs are
unstructured, filtered by level, and designed for debugging — not
for answering "who did what, when, and was it allowed?"

Enterprise deployments need:

- **Compliance evidence** — demonstrable record of access for
  auditors.
- **Incident investigation** — reconstruct what happened around a
  security event.
- **Anomaly detection** — feed structured events into monitoring
  systems.
- **Accountability** — attribute actions to identities across
  workspaces.

The current logging infrastructure cannot serve these needs because
it is unstructured, inconsistently formatted, and interleaves
debug noise with security-relevant signals.

## Design Principles

- **Complete.**  Every gateway request and every IAM decision emits
  an event.  No sampling, no level-gating.  The pub/sub cost is
  negligible; consumers filter what they need.

- **Structured.**  Events are typed, versioned, machine-parseable
  JSON objects with a fixed envelope and operation-specific payloads.
  No free-text messages.

- **Cheap to produce.**  Events land on a pub/sub topic.  No
  synchronous writes, no blocking on consumer availability.  If no
  consumer is subscribed, events are discarded by the broker — that
  is acceptable.

- **Rich.**  Events carry enough context to reconstruct the full
  security narrative without correlating against operational logs.
  Identity, workspace, capability, resource, outcome, timing,
  client metadata.

- **Immutable.**  Once emitted, an event is a fact.  Consumers may
  filter, aggregate, or discard events, but never mutate them.

- **Decoupled.**  Producers (gateway, IAM service) have no knowledge
  of consumers.  The topic is fire-and-forget.  This keeps the
  critical path fast and allows diverse consumer deployments.

## Architecture

### Event transport

Audit events are published to a dedicated pub/sub topic, declared
in the schema layer following the project's queue naming convention:

```python
audit_events_queue = queue('audit-events', cls='notify')
```

This produces the queue identifier `notify:tg:audit-events`, which
each backend maps to its native topic format (e.g. Pulsar maps
`notify` to `non-persistent://tg/notify/audit-events`).

The `notify` class is the right fit: non-persistent, per-subscriber
delivery, no competing-consumer semantics.  Audit event production
must never block the gateway or IAM service.  Consumers that need
durability persist events themselves on receipt.

A single topic carries all event types, distinguished by the
`event_type` field in the envelope.  This simplifies producer
logic and allows consumers to subscribe once and filter client-side.

### Producers

Two components emit audit events:

1. **API Gateway** — emits a `gateway.request` event for every
   inbound HTTP/WebSocket request after the request completes
   (or fails).

2. **IAM Service** — emits `iam.authenticate` and `iam.authorise`
   events for every authentication and authorisation decision.

Both producers emit asynchronously — the event is published after
the response is sent (gateway) or after the decision is returned
(IAM).  Audit emission is never on the critical path.

### Consumers

Not defined by this spec.  Example consumers that deployments
may wire up:

- Append to an immutable log store (S3, Cassandra, ClickHouse).
- Forward to a SIEM (Splunk, Elastic, Sentinel).
- Aggregate for billing/metering.
- Feed an anomaly detection model.
- Write to stdout for development debugging.

## Event Envelope

Every audit event shares a common envelope:

```json
{
  "schema_version": 1,
  "event_id": "uuid-v4",
  "event_type": "gateway.request",
  "timestamp": "2026-07-05T14:23:01.123Z",
  "producer": "api-gateway",
  "payload": { ... }
}
```

| Field | Type | Description |
|---|---|---|
| `schema_version` | int | Envelope schema version.  Consumers must ignore events with versions they don't understand. |
| `event_id` | string | Globally unique event identifier (UUID v4). |
| `event_type` | string | Dot-separated event type from the vocabulary below. |
| `timestamp` | string | ISO 8601 UTC timestamp at event emission. |
| `producer` | string | Component identity that emitted the event. |
| `payload` | object | Event-type-specific structured data. |

## Event Types

### `gateway.request`

Emitted by the API gateway for every completed request.

```json
{
  "request_id": "uuid-v4",
  "method": "POST",
  "path": "/api/v1/flow/default/graph-rag",
  "capability": "graph-rag:query",
  "workspace": "production",
  "identity": "user:mark",
  "client_ip": "192.168.1.42",
  "user_agent": "trustgraph-cli/2.6.11",
  "status_code": 200,
  "outcome": "success",
  "duration_ms": 1423,
  "request_size_bytes": 256,
  "response_size_bytes": 4096,
  "parameters": {
    "collection": "default",
    "entity_limit": 50
  }
}
```

| Field | Type | Description |
|---|---|---|
| `request_id` | string | Unique ID for this request, propagated to IAM events for correlation. |
| `method` | string | HTTP method. |
| `path` | string | Request path (no query string). |
| `capability` | string | The capability required for this endpoint (from the capability vocabulary). |
| `workspace` | string | Resolved workspace for this request. |
| `identity` | string | Authenticated identity handle, or `"anonymous"` if unauthenticated. |
| `client_ip` | string | Client IP address (may be from X-Forwarded-For). |
| `user_agent` | string | Client User-Agent header. |
| `status_code` | int | HTTP response status code. |
| `outcome` | string | One of `success`, `denied`, `error`, `unauthenticated`. |
| `duration_ms` | int | Request duration in milliseconds. |
| `request_size_bytes` | int | Request body size. |
| `response_size_bytes` | int | Response body size. |
| `error` | string | Error category.  Present only when outcome is not `success`. |
| `parameters` | object | Operation-specific parameters extracted from the request (not the full body — only semantically relevant fields). |

### `iam.authenticate`

Emitted by the IAM service for every authentication attempt.

```json
{
  "request_id": "uuid-v4",
  "credential_type": "api-key",
  "identity": "user:mark",
  "outcome": "success",
  "client_ip": "192.168.1.42",
  "key_id": "key-abc123"
}
```

| Field | Type | Description |
|---|---|---|
| `request_id` | string | Correlates with the gateway request that triggered this authentication. |
| `credential_type` | string | One of `api-key`, `jwt`, `login-password`. |
| `identity` | string | Resolved identity on success, or `"unknown"` on failure. |
| `outcome` | string | One of `success`, `failure`. |
| `failure_reason` | string | Internal failure category (not exposed to clients): `invalid-key`, `expired-jwt`, `bad-signature`, `user-disabled`, `unknown-user`.  Present only on failure. |
| `client_ip` | string | Forwarded from the gateway request. |
| `key_id` | string | API key identifier (not the secret).  Present only on key-based auth. |

**Note:** `failure_reason` is for the audit log only.  The client
response is always the same masked error per the IAM contract's
security rule.  The audit consumer sees the real reason; the
attacker does not.

### `iam.authorise`

Emitted by the IAM service for every authorisation decision.

```json
{
  "request_id": "uuid-v4",
  "identity": "user:mark",
  "capability": "graph-rag:query",
  "workspace": "production",
  "resource": "flow:default",
  "outcome": "allow",
  "evaluated_roles": ["workspace-user"],
  "evaluation_time_us": 42
}
```

| Field | Type | Description |
|---|---|---|
| `request_id` | string | Correlates with the gateway request. |
| `identity` | string | Identity being authorised. |
| `capability` | string | Capability being checked. |
| `workspace` | string | Workspace scope of the resource. |
| `resource` | string | Structured resource identifier. |
| `outcome` | string | One of `allow`, `deny`. |
| `denial_reason` | string | Why denied: `no-matching-role`, `capability-not-in-role`, `workspace-not-accessible`, `user-disabled`.  Present only on denial. |
| `evaluated_roles` | list of string | Roles evaluated during the decision (OSS regime specific — other regimes may populate differently). |
| `evaluation_time_us` | int | Time to evaluate the decision in microseconds. |

### `iam.management`

Emitted by the IAM service for administrative mutations.

```json
{
  "request_id": "uuid-v4",
  "actor": "user:admin",
  "operation": "create-user",
  "target_identity": "user:new-hire",
  "target_workspace": "engineering",
  "outcome": "success",
  "details": {
    "roles_assigned": ["workspace-user"]
  }
}
```

| Field | Type | Description |
|---|---|---|
| `request_id` | string | Correlates with the gateway request. |
| `actor` | string | Identity performing the action. |
| `operation` | string | IAM operation name (`create-user`, `delete-api-key`, `assign-role`, `create-workspace`, etc.). |
| `target_identity` | string | Identity being acted upon.  Present only when applicable. |
| `target_workspace` | string | Workspace being acted upon.  Present only when applicable. |
| `outcome` | string | One of `success`, `error`. |
| `details` | object | Operation-specific details (roles assigned, key created, etc.). |

## Correlation

All events from a single gateway request share the same
`request_id`.  A typical request produces:

1. One `gateway.request` event (after completion).
2. One `iam.authenticate` event (credential validation).
3. One or more `iam.authorise` events (capability checks).

Consumers can reconstruct the full request lifecycle by grouping
on `request_id`.

## Implementation

### Gateway changes

The gateway emits `gateway.request` events.  Implementation:

- Assign a UUID `request_id` at request entry.
- Pass `request_id` and `client_ip` to the IAM service in the
  `IamRequest` (new fields on the dataclass).
- After the response is sent, publish the audit event to the
  audit topic.  This is a non-blocking fire-and-forget publish.

### IAM service changes

The IAM service emits `iam.authenticate`, `iam.authorise`, and
`iam.management` events.  Implementation:

- Accept `request_id` and `client_ip` from the gateway on each
  `IamRequest`.
- After each decision or mutation, publish the corresponding audit
  event.  Non-blocking.

### Schema additions

New queue declaration in `trustgraph-base/trustgraph/schema/`:

```python
from trustgraph.schema.core.topic import queue

audit_events_queue = queue('audit-events', cls='notify')
```

New fields on `IamRequest`:

```python
@dataclass
class IamRequest:
    ...
    request_id: str = ""
    client_ip: str = ""
```

These are informational — the IAM service does not act on them
beyond echoing them into audit events.

### Pub/sub producer

A lightweight audit publisher utility in `trustgraph-base`:

```python
class AuditPublisher:
    def __init__(self, producer):
        self.producer = producer

    async def emit(self, event_type, payload):
        event = {
            "schema_version": 1,
            "event_id": str(uuid4()),
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "producer": self.component_name,
            "payload": payload,
        }
        await self.producer.send(json.dumps(event).encode())
```

The publisher is instantiated once per component and shared across
request handlers.

## What This Spec Does Not Cover

- **Storage.**  Where audit events are persisted, for how long,
  and in what format.  Deployment-specific.
- **Alerting.**  What conditions trigger alerts.  Consumer logic.
- **Retention policy.**  How long events are kept.  Compliance-
  dependent.
- **UI.**  Audit log viewers, dashboards, search interfaces.
- **Filtering/routing.**  Topic partitioning, consumer-side
  filtering, event routing to different backends.
- **Redaction.**  PII handling in audit events (may be needed for
  GDPR — a future concern for enterprise consumers).

These are all consumer-side concerns.  The value of this boundary
is that producers remain simple and fast while consumers can be
as sophisticated as the deployment requires.

## Open Questions

- **Should WebSocket upgrade events emit separately from per-message
  events?**  Current proposal: one `gateway.request` per WebSocket
  session (on close), with `duration_ms` covering the full session.
  Per-message audit for long-lived sockets (e.g. streaming RAG) may
  be needed for metering but adds volume.

- **Should `parameters` in `gateway.request` be standardised per
  endpoint, or free-form?**  Standardised is more useful for
  consumers but requires maintenance as endpoints evolve.

- **Event ordering guarantees.**  Pub/sub does not guarantee
  ordering across partitions.  Consumers that need strict ordering
  must sort by `timestamp` or `request_id` sequence.

## References

- [IAM Contract](iam-contract.md) — the authentication/authorisation
  abstraction.
- [IAM Protocol](iam-protocol.md) — the OSS regime wire protocol.
- [Capability Vocabulary](capabilities.md) — the capability strings
  used in authorisation and audit events.
- [Logging Strategy](logging-strategy.md) — operational logging
  (complementary, not overlapping).
