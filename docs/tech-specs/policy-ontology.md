---
layout: default
title: "Policy Ontology"
parent: "Tech Specs"
---

# Policy Ontology

The policy ontology defines the application-specific concepts
that SHACL-AF does not provide: determination types, audit
records, and override tracking. The rule structure itself
(targets, conditions, rule bodies) is expressed using SHACL's
own vocabulary.

See also:
- [Policy Filtering Overview](policy-filtering.md) — problem
  statement and SHACL-AF rationale
- [Policy Audit Events](policy-audit-events.md) — audit event
  types and payloads
- [Policy Examples](policy-examples.md) — worked examples

## Conceptual Model

Four application-specific concepts extend SHACL-AF:

**DeterminationType** — the outcome a policy produces when its
target and conditions are satisfied. Information is either
presented or removed — there is no transformation or redaction.
Three determination types distinguish the operational meaning
and audit severity:

- **Notify** — access is permitted and data passes through
  untouched, but the policy emits an event recording that the
  rule fired. Use cases include debug tracing and recording
  access to sensitive-but-allowed information. The audit
  record is informational.
- **Filtered** — a valid query caught data that exceeds the
  user's scope (over-retrieval). This is normal operation —
  a broad graph traversal will routinely pull in triples
  the user is not entitled to see. Matched triples are removed
  silently. Standard policy evaluation audit record.
- **Violation** — the query crossed an explicit security
  barrier (e.g. Chinese Wall, unauthorised scope probe).
  The query or subject is blocked; response withheld or
  sanitised. High-severity security event logged with
  optional telemetry alert or circuit breaker.

The default — no policy matches — is implicit allow with no
event. The three explicit determinations above all produce
audit events; the distinction between Filtered and Violation
is invisible to the user — in both cases data is simply
absent from the response. The difference is in the audit
signal: Filtered is routine housekeeping, Violation is a
security event that may warrant investigation.

**PolicyEvaluation** — the audit record produced each time a
policy is evaluated against a query. Records the policy shape,
the user context, the determination, the matched data, the
reason, and a timestamp. Evaluations are persisted to an audit
graph for regulatory and operational review.

**Override** — a record of an authorised user bypassing a policy
determination. References the evaluation being overridden, the
user exercising override authority, the authority cited, the
justification, and an expiry condition. Overrides are scoped to
a specific evaluation, not to the policy in general.

Policy rules themselves are `sh:NodeShape` instances with
`sh:SPARQLTarget` or `sh:SPARQLRule` — standard SHACL-AF, not
custom classes. The ontology adds metadata properties
(`tg-pol:appliesTo`, `tg-pol:effectiveFrom`, `tg-pol:effectiveTo`)
to policy shapes for lifecycle management without inventing a
parallel rule structure.

## Relationships

```
sh:NodeShape (policy)
    ├── sh:target ──▶ sh:SPARQLTarget
    ├── sh:rule ──▶ sh:SPARQLRule / sh:TripleRule
    ├── sh:condition ──▶ sh:NodeShape
    ├── sh:order ──▶ xsd:decimal
    ├── tg-pol:producesDetermination ──▶ tg-pol:DeterminationType (Notify/Filtered/Violation)
    ├── tg-pol:appliesTo ──▶ (role IRI)
    └── tg-pol:effectiveFrom / effectiveTo ──▶ xsd:dateTime

PolicyEvaluation
    ├── tg-pol:evaluatedPolicy ──▶ sh:NodeShape (policy)
    ├── tg-pol:evaluatedNode ──▶ (target resource IRI)
    ├── tg-pol:determination ──▶ tg-pol:DeterminationType
    ├── tg-pol:userContext ──▶ (user context IRI)
    ├── tg-pol:reason ──▶ xsd:string
    └── tg-pol:evaluatedAt ──▶ xsd:dateTime

Override
    ├── tg-pol:overrides ──▶ PolicyEvaluation
    ├── tg-pol:exercisedBy ──▶ (user IRI)
    ├── tg-pol:authority ──▶ (authority IRI)
    ├── tg-pol:justification ──▶ xsd:string
    └── tg-pol:expiresAt ──▶ xsd:dateTime
```

## Storage

Policies are stored in the named graph `urn:graph:policy` within
the same collection as the data they govern. The policy engine
fetches applicable policies at query time by querying this graph
for `sh:NodeShape` instances, filtered by `tg-pol:appliesTo`
against the user context's roles and by `tg-pol:effectiveFrom` /
`tg-pol:effectiveTo` against the current time.

## Ontology

```turtle
@prefix tg-pol: <https://trustgraph.ai/ontology/policy/> .
@prefix sh:     <http://www.w3.org/ns/shacl#> .
@prefix rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs:   <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl:    <http://www.w3.org/2002/07/owl#> .
@prefix xsd:    <http://www.w3.org/2001/XMLSchema#> .

# -------------------------------------------------------------
# Ontology declaration
# -------------------------------------------------------------

tg-pol: a owl:Ontology ;
    rdfs:label "TrustGraph Policy Ontology" ;
    rdfs:comment "Application-specific extensions to SHACL-AF for policy determination, audit, and override tracking. Policy rules themselves are standard sh:NodeShape instances with SHACL-AF targets and rules." .

# -------------------------------------------------------------
# Classes
# -------------------------------------------------------------

tg-pol:DeterminationType a owl:Class ;
    rdfs:label "Determination Type" ;
    rdfs:comment "The outcome produced when a policy shape's target and conditions are satisfied. Determines both the action on the result set and the audit severity." .

tg-pol:PolicyEvaluation a owl:Class ;
    rdfs:label "Policy Evaluation" ;
    rdfs:comment "Audit record of a policy shape evaluated against a specific query and user context." .

tg-pol:Override a owl:Class ;
    rdfs:label "Override" ;
    rdfs:comment "Record of an authorised user bypassing a policy determination, scoped to a specific evaluation." .

# -------------------------------------------------------------
# Determination type individuals
# -------------------------------------------------------------

tg-pol:Notify a tg-pol:DeterminationType ;
    rdfs:label "Notify" ;
    rdfs:comment "Access permitted and data passes through untouched. Policy emits an informational event recording that the rule fired. For debug tracing and sensitive-but-allowed access logging." .

tg-pol:Filtered a tg-pol:DeterminationType ;
    rdfs:label "Filtered" ;
    rdfs:comment "Valid query caught data exceeding user scope (over-retrieval). Matched triples removed silently. Standard policy evaluation audit record." .

tg-pol:Violation a tg-pol:DeterminationType ;
    rdfs:label "Violation" ;
    rdfs:comment "Query crossed an explicit security barrier. Query or subject blocked; response withheld or sanitised. High-severity security event logged." .

# -------------------------------------------------------------
# Policy shape metadata properties
#
# These extend sh:NodeShape instances that serve as policy
# rules, adding lifecycle and role-targeting metadata.
# -------------------------------------------------------------

tg-pol:producesDetermination a owl:ObjectProperty ;
    rdfs:label "produces determination" ;
    rdfs:comment "The determination type this policy shape produces when its target and rules are satisfied." ;
    rdfs:domain sh:NodeShape ;
    rdfs:range tg-pol:DeterminationType .

tg-pol:appliesTo a owl:ObjectProperty ;
    rdfs:label "applies to" ;
    rdfs:comment "User context role IRI that activates this policy. Absent means the policy applies to all roles." ;
    rdfs:domain sh:NodeShape .

tg-pol:effectiveFrom a owl:DatatypeProperty ;
    rdfs:label "effective from" ;
    rdfs:comment "Start of this policy's validity period." ;
    rdfs:domain sh:NodeShape ;
    rdfs:range xsd:dateTime .

tg-pol:effectiveTo a owl:DatatypeProperty ;
    rdfs:label "effective to" ;
    rdfs:comment "End of this policy's validity period. Absent means no expiry." ;
    rdfs:domain sh:NodeShape ;
    rdfs:range xsd:dateTime .

# -------------------------------------------------------------
# Policy evaluation properties
# -------------------------------------------------------------

tg-pol:evaluatedPolicy a owl:ObjectProperty ;
    rdfs:label "evaluated policy" ;
    rdfs:comment "The policy shape that was evaluated." ;
    rdfs:domain tg-pol:PolicyEvaluation ;
    rdfs:range sh:NodeShape .

tg-pol:evaluatedNode a owl:ObjectProperty ;
    rdfs:label "evaluated node" ;
    rdfs:comment "The specific focus node or target resource IRI that triggered the determination. Bound from $this in the SHACL-AF rule." ;
    rdfs:domain tg-pol:PolicyEvaluation .

tg-pol:determination a owl:ObjectProperty ;
    rdfs:label "determination" ;
    rdfs:domain tg-pol:PolicyEvaluation ;
    rdfs:range tg-pol:DeterminationType .

tg-pol:userContext a owl:ObjectProperty ;
    rdfs:label "user context" ;
    rdfs:comment "The user context against which this policy was evaluated." ;
    rdfs:domain tg-pol:PolicyEvaluation .

tg-pol:reason a owl:DatatypeProperty ;
    rdfs:label "reason" ;
    rdfs:comment "Human-readable justification for the determination, produced by the SHACL rule's CONSTRUCT." ;
    rdfs:domain tg-pol:PolicyEvaluation ;
    rdfs:range xsd:string .

tg-pol:evaluatedAt a owl:DatatypeProperty ;
    rdfs:label "evaluated at" ;
    rdfs:domain tg-pol:PolicyEvaluation ;
    rdfs:range xsd:dateTime .

# -------------------------------------------------------------
# Override properties
# -------------------------------------------------------------

tg-pol:overrides a owl:ObjectProperty ;
    rdfs:label "overrides" ;
    rdfs:comment "The policy evaluation this override bypasses." ;
    rdfs:domain tg-pol:Override ;
    rdfs:range tg-pol:PolicyEvaluation .

tg-pol:exercisedBy a owl:ObjectProperty ;
    rdfs:label "exercised by" ;
    rdfs:comment "The user who exercised override authority." ;
    rdfs:domain tg-pol:Override .

tg-pol:authority a owl:ObjectProperty ;
    rdfs:label "authority" ;
    rdfs:comment "The override authority IRI cited for this override." ;
    rdfs:domain tg-pol:Override .

tg-pol:justification a owl:DatatypeProperty ;
    rdfs:label "justification" ;
    rdfs:comment "Free-text justification for why the override was exercised." ;
    rdfs:domain tg-pol:Override ;
    rdfs:range xsd:string .

tg-pol:expiresAt a owl:DatatypeProperty ;
    rdfs:label "expires at" ;
    rdfs:comment "When this override ceases to be effective." ;
    rdfs:domain tg-pol:Override ;
    rdfs:range xsd:dateTime .
```
