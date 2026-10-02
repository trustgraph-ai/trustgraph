---
layout: default
title: "Policy Ontology"
parent: "Tech Specs"
---

# Policy Ontology

The policy ontology defines the application-specific concepts
that SHACL-AF does not provide. The rule structure itself
(targets, conditions, rule bodies) is expressed using SHACL's
own vocabulary. Policy evaluation output uses the W3C standard
`sh:ValidationResult`, extended with a single custom property
`tg-pol:blocks` to control whether matched nodes are removed
from query results.

See also:
- [Policy Filtering Overview](policy-filtering.md) — problem
  statement and SHACL-AF rationale
- [Policy Audit Events](policy-audit-events.md) — audit event
  types and payloads
- [Policy Examples](policy-examples.md) — worked examples

## Conceptual Model

Two application-specific concepts extend SHACL-AF:

**Determination** — the outcome a policy produces, expressed as
an IRI in the `sh:resultSeverity` field of an `sh:ValidationResult`.
The IRI is not restricted to a fixed set — policy authors choose
IRIs that reflect their domain semantics (e.g.
`tg-pol:Filtered`, `tg-pol:Violation`, `tg-pol:SensitiveAccess`,
or any organisation-specific IRI). The determination IRI is
reported as-is in the policy audit event payload.

The `tg-pol:blocks` property on the ValidationResult controls
whether the matched node is removed from query results. When
`true` (the default if omitted), the node's triples are removed.
When `false`, the data passes through untouched but the policy
event is still emitted. This allows policies that log access
without restricting it.

The default — no policy matches a node — is implicit allow
with no event emitted.

**Override** — a record of an authorised user bypassing a policy
determination. References the evaluation being overridden, the
user exercising override authority, the authority cited, the
justification, and an expiry condition. Overrides are scoped to
a specific evaluation, not to the policy in general.

Policy rules themselves are `sh:NodeShape` instances with
`sh:SPARQLTarget` and `sh:SPARQLRule` — standard SHACL-AF, not
custom classes. The ontology adds metadata properties
(`tg-pol:appliesTo`, `tg-pol:effectiveFrom`, `tg-pol:effectiveTo`)
to policy shapes for lifecycle management without inventing a
parallel rule structure.

## Relationships

```
sh:NodeShape (policy)
    ├── sh:target ──▶ sh:SPARQLTarget
    ├── sh:rule ──▶ sh:SPARQLRule
    ├── sh:condition ──▶ sh:NodeShape
    ├── sh:order ──▶ xsd:decimal
    ├── tg-pol:appliesTo ──▶ (role IRI)
    └── tg-pol:effectiveFrom / effectiveTo ──▶ xsd:dateTime

sh:ValidationResult (CONSTRUCT output)
    ├── sh:focusNode ──▶ (evaluated node IRI)
    ├── sh:sourceShape ──▶ sh:NodeShape (policy)
    ├── sh:resultSeverity ──▶ (determination IRI — any IRI)
    ├── sh:resultMessage ──▶ xsd:string
    └── tg-pol:blocks ──▶ xsd:boolean (default true)

Override
    ├── tg-pol:overrides ──▶ sh:ValidationResult
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

## Policy enforcement mode

The presence of policies in `urn:graph:policy` determines
whether access control is active. If the policy graph contains
at least one `sh:NodeShape`, the system is in enforcement mode
and every request must include a `user_context`. A request
without `user_context` when policies exist is a validation
error — rejected with an error response, no triples returned.

If the policy graph is empty, the system is in open mode —
`user_context` is optional and all triples pass through.

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
    rdfs:comment "Application-specific extensions to SHACL-AF for policy evaluation and override tracking. Policy evaluation output uses standard sh:ValidationResult with a custom tg-pol:blocks property. Determination severity is any IRI chosen by the policy author." .

# -------------------------------------------------------------
# Classes
# -------------------------------------------------------------

tg-pol:Override a owl:Class ;
    rdfs:label "Override" ;
    rdfs:comment "Record of an authorised user bypassing a policy determination, scoped to a specific evaluation." .

# -------------------------------------------------------------
# ValidationResult extension property
# -------------------------------------------------------------

tg-pol:blocks a owl:DatatypeProperty ;
    rdfs:label "blocks" ;
    rdfs:comment "Controls whether the matched node is removed from query results. Default is true (block). Set to false to log access without restricting it." ;
    rdfs:domain sh:ValidationResult ;
    rdfs:range xsd:boolean .

# -------------------------------------------------------------
# Policy shape metadata properties
#
# These extend sh:NodeShape instances that serve as policy
# rules, adding lifecycle and role-targeting metadata.
# -------------------------------------------------------------

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
# Override properties
# -------------------------------------------------------------

tg-pol:overrides a owl:ObjectProperty ;
    rdfs:label "overrides" ;
    rdfs:comment "The validation result this override bypasses." ;
    rdfs:domain tg-pol:Override ;
    rdfs:range sh:ValidationResult .

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
