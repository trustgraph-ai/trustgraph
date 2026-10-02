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

## Event Type

A single event type is used for all policy evaluations:

- **`policy.evaluation`** — a policy matched one or more nodes
  during query filtering. The determination IRI in the payload
  identifies the nature of the match. Event consumers decide
  how to handle each determination based on the IRI — the
  publisher does not impose a severity classification.

## Event Payload

Each audit event payload contains:

| Field            | Description                                          |
|------------------|------------------------------------------------------|
| `request_id`     | Correlates all events from a single query request    |
| `policy_uri`     | URI of the policy shape that matched                 |
| `policy_label`   | Human-readable label of the policy                   |
| `determination`  | Determination IRI from `sh:resultSeverity`           |
| `blocks`         | Whether matched nodes were removed from results      |
| `user_context`   | Full user context (ID, roles, org units, assignments, entitlements, overrides, delegation) |
| `node_iris`      | Node IRIs affected (capped at 100 per event)         |
| `node_count`     | Total number of affected nodes (may exceed list size) |
| `reason`         | Human-readable reason from `sh:resultMessage`        |
| `query_s`        | Subject term from the triggering query (or null)     |
| `query_p`        | Predicate term from the triggering query (or null)   |
| `query_o`        | Object term from the triggering query (or null)      |
| `workspace`      | Workspace the query was executed in                  |
| `collection`     | Collection the query targeted                        |
| `graph`          | Named graph the query targeted (empty = default)     |

The `request_id` ties together all events from a single query.
When streaming produces multiple batches, each batch may emit
its own events — the `request_id` allows consumers to
reconstruct the complete picture.

The `determination` field is the raw IRI from
`sh:resultSeverity` in the CONSTRUCT output. It is not
constrained to a fixed set — policy authors choose IRIs that
reflect their domain (e.g. `tg-pol:Filtered`,
`tg-pol:Violation`, `tg-pol:SensitiveAccess`, or any
organisation-specific IRI).

The query parameters (`query_s`, `query_p`, `query_o`,
`collection`, `graph`) give the full context of what the user
was asking for when the policy fired. The full user context is
included so that an auditor can reconstruct the policy decision
— the org units, assignments, and entitlements that determined
which policies matched.

## Operational Semantics

The interpretation of policy events depends on the determination
IRI. Two common patterns:

Blocking determinations (`tg-pol:blocks true`) where the
determination indicates routine over-retrieval (e.g.
`tg-pol:Filtered`) are expected in normal operation — a broad
graph traversal will routinely retrieve nodes outside the user's
scope. These are routine housekeeping records for compliance
review.

Blocking determinations where the determination indicates a
security boundary crossing (e.g. `tg-pol:Violation`) signal
that a security boundary was probed and may warrant
investigation or automated response (circuit breaker, alert
escalation).

Non-blocking determinations (`tg-pol:blocks false`) record
access that was permitted but noteworthy — sensitive data
accessed by a properly authorised user, debug tracing, or
regulatory access logging.

Event consumers subscribe to the `policy-events` queue and
filter on the determination IRI to route events to the
appropriate response.

## Node IRI Batching

The `node_iris` list is capped at 100 per event. The `node_count`
field always contains the true total number of affected nodes,
so consumers can detect truncation. For most blocking events on
narrow queries the cap will not be reached; for broad queries it
may be, but 100 IRIs is sufficient to investigate the pattern.
