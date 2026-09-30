---
layout: default
title: "Policy Audit Events"
parent: "Tech Specs"
---

# Policy Audit Events

The policy filter emits audit events for compliance review and
security monitoring. Events are published to the `policy-events`
queue (`notify:tg:policy-events`), a system-wide broadcast queue
— any subscriber receives all policy events across all workspaces
and flows.

See also:
- [Policy Filtering Overview](policy-filtering.md) — problem
  statement and SHACL-AF rationale
- [Policy Ontology](policy-ontology.md) — vocabulary and
  determination types
- [Audit Events](audit-events.md) — general audit event
  infrastructure

## Event Types

Three event types correspond to the three determination types:

- **`policy.notify`** — node passed policy evaluation but the
  policy emits an informational event. For debug tracing and
  recording access to sensitive-but-allowed information.
- **`policy.filtered`** — node removed by routine over-retrieval
  filtering. Standard audit record for compliance review.
- **`policy.violation`** — node triggered a security barrier.
  High-severity event for investigation and alerting.

## Event Payload

Each audit event payload contains:

| Field            | Description                                          |
|------------------|------------------------------------------------------|
| `policy_uri`     | URI of the policy shape that matched                 |
| `policy_label`   | Human-readable label of the policy                   |
| `determination`  | `Notify`, `Filtered`, or `Violation`                 |
| `user_context`   | Full user context (ID, roles, org units, assignments, entitlements, overrides, delegation) |
| `node_iris`      | Node IRIs affected (capped at 100 per event)         |
| `node_count`     | Total number of affected nodes (may exceed list size) |
| `reason`         | Policy's reason string                               |
| `query_s`        | Subject term from the triggering query (or null)     |
| `query_p`        | Predicate term from the triggering query (or null)   |
| `query_o`        | Object term from the triggering query (or null)      |
| `workspace`      | Workspace the query was executed in                  |
| `collection`     | Collection the query targeted                        |
| `graph`          | Named graph the query targeted (empty = default)     |

The query parameters (`query_s`, `query_p`, `query_o`, `collection`,
`graph`) give the full context of what the user was asking for when
the policy fired. The full user context is included so that an
auditor can reconstruct the policy decision — the org units,
assignments, and entitlements that determined which policies matched.

## Operational Semantics

Filtered events are expected in normal operation — a broad graph
traversal will routinely retrieve nodes outside the user's scope.
These are routine housekeeping records for compliance review.

Violation events signal that a security boundary was probed and
may warrant investigation or automated response (circuit breaker,
alert escalation). In practice, violation node counts should be
small — a user probing a classification barrier or information
wall will typically trigger on a handful of nodes.

## Node IRI Batching

The `node_iris` list is capped at 100 per event. The `node_count`
field always contains the true total number of affected nodes,
so consumers can detect truncation. For most violation events the
cap will not be reached; for filtered events on broad queries it
may be, but 100 IRIs is sufficient to investigate the pattern.
