---
layout: default
title: "Policy Filtering Technical Specification"
parent: "Tech Specs"
---

# Policy Filtering Technical Specification

## Overview

This specification describes the policy filtering layer that
determines what data a user may see when querying the knowledge
graph. It covers the problem space, the policy language, how
policies are stored in the graph, and the evaluation model.

## Problem Statement

A shared knowledge graph contains data from multiple sources,
about multiple entities, at multiple sensitivity levels. Different
users need different views of the same graph — not because of
workspace separation (which is a deployment boundary) but because
of who they are, what they're doing, and what policies govern
their access.

### The same data, different viewers

Consider an enterprise graph containing client records, internal
research, deal intelligence, and operational data. A relationship
manager should see their assigned clients' data but not other
clients'. A compliance officer should see audit trails across the
organisation but not deal-specific intelligence. A client logging
into a portal should see their own holdings and nothing else.

These are not edge cases — they are the normal operating mode of
any multi-user system built on a shared graph.

### Information barriers within the same organisation

Organisations routinely erect barriers between groups that must
not share information, even though they work for the same company
and query the same graph. The classic case is Chinese Walls in
financial services: buy-side and sell-side teams on the same deal
must not see each other's intelligence. But the pattern is
general:

- A law firm where two partners advise opposing parties in a
  dispute. Both query the firm's knowledge graph, but neither
  should see the other's case materials.
- A pharmaceutical company where the clinical trials team and the
  commercial team must be isolated to prevent inside information
  leaking into marketing decisions.
- A consultancy where competing client engagements must not
  cross-contaminate.

These barriers are dynamic — they activate when a conflict arises
and deactivate when it resolves. They cannot be modelled as static
permissions on folders or tables.

### The same person, different roles

A single user may legitimately need different views of the graph
depending on what role they are acting in at the time. A doctor
who is also a patient at the same hospital should see all records
when acting as treating physician and only their own records when
acting as patient. A portfolio manager who is also a personal
investor should see all managed accounts in their professional
role but only their personal account when acting as a retail
client.

The access decision depends not just on who the user is but on
which hat they are currently wearing — captured by the user
context's role field.

### Pre-context pruning for AI safety

When the graph feeds an LLM — for RAG synthesis, report
generation, or conversational queries — the policy boundary must
sit upstream of the model. Data that a user should not see must
never enter the LLM's context window. This is a structural
guarantee: the model cannot leak what it was never given,
regardless of prompt injection attacks or instruction-following
failures.

Post-hoc redaction (letting the LLM see everything and then
filtering the output) is not acceptable. The policy engine prunes
the graph before context assembly, not after.

### Why static permissions don't work

Traditional file-and-folder permissions answer "is this user
allowed to access this resource?" — a binary gate on a named
object. Knowledge graph access is fundamentally different:

- **The resource is a traversal, not a document.** A query like
  "show me my portfolio exposure by sector" traverses account
  nodes, holding nodes, security nodes, and classification nodes.
  Policy must scope the traversal at the account level while
  allowing it through shared reference data.
- **Shared reference data must be accessible without leaking
  private data.** The fact that "AAPL is classified as Technology"
  is public. The fact that "Client A holds 5,000 shares of AAPL"
  is private. Both live in the same graph.
- **Absence of data must not be informative.** A policy-filtered
  response must be structurally indistinguishable from a response
  where the filtered data never existed. No "access denied"
  markers, no empty placeholders, no differences in response shape
  that reveal the existence of hidden data.

## Policy Representation: SHACL-AF

Policies are expressed using SHACL Advanced Features (SHACL-AF),
the W3C standard for graph validation and rule evaluation.
SHACL-AF is not a future compilation target — it is how policies
are represented, stored, and evaluated.

### Why SHACL-AF

SHACL was designed to validate RDF graphs against conditions.
SHACL Advanced Features extends it with capabilities that make
it suitable for policy evaluation:

- **Custom targets (`sh:SPARQLTarget`)** select focus nodes
  dynamically using SPARQL. A policy that applies to "all
  triples whose subject is assigned to the requesting user"
  requires a query that joins user context with data — not
  simple class-based targeting.
- **SPARQL rules (`sh:SPARQLRule`)** execute CONSTRUCT queries
  with the focus node pre-bound as `$this`. The rule traverses
  graph paths, evaluates conditions, and produces determination
  triples.
- **Triple rules (`sh:TripleRule`)** compose simple
  subject-predicate-object determinations from node expressions,
  suitable for straightforward policies.
- **`sh:order`** controls rule execution order within a shape
  and across shapes, handling priority when multiple policies
  match.
- **Monotonic inference** — SHACL rules add triples to an
  inference graph without modifying the original data. Policy
  determinations annotate the data graph rather than changing
  it, preserving the separation between asserted facts and
  policy evaluations.

A policy expressed as a SHACL-AF shape has four parts:

1. **Target** — which graph nodes the policy applies to
   (`sh:targetClass`, `sh:targetNode`, or `sh:SPARQLTarget`)
2. **Condition** — prerequisites that must hold before the rule
   fires (`sh:condition` referencing other shapes)
3. **Rule body** — the evaluation logic (`sh:SPARQLRule` with a
   CONSTRUCT query, or `sh:TripleRule` with node expressions)
4. **Determination** — the output triples, inferred into the
   policy evaluation graph

### Interaction with user context

At query time, the user context is injected into the evaluation
graph as a set of triples describing the current accessor. SHACL
rules reference user context properties in their targets and
conditions using the same SPARQL patterns used for data graph
properties.

The user context lives in an ephemeral named graph for the
duration of the query. Policies live in `urn:graph:policy`. The
data lives in the default graph (or domain-specific named
graphs). The SHACL engine evaluates rules across all three.

## Policy Ontology

The policy ontology defines the application-specific concepts
that SHACL-AF does not provide: determination types, audit
records, and override tracking. The rule structure itself
(targets, conditions, rule bodies) is expressed using SHACL's
own vocabulary.

### Conceptual Model

Four application-specific concepts extend SHACL-AF:

**DeterminationType** — the outcome a policy produces when its
target and conditions are satisfied. Information is either
presented or removed — there is no transformation or redaction.
Three determination types distinguish the operational meaning
and audit severity:

- **Allowed** — the information is fully compliant with policy.
  Matched triples are included in the response without
  modification. Standard query log.
- **Filtered** — a valid query caught data that exceeds the
  user's scope (over-retrieval). This is normal operation —
  a broad graph traversal will routinely pull in triples
  the user is not entitled to see. Matched triples are removed
  silently without trace. Standard policy evaluation audit
  record.
- **Violation** — the query crossed an explicit security
  barrier (e.g. Chinese Wall, unauthorised scope probe).
  The query or subject is blocked; response withheld or
  sanitised. High-severity security event logged with
  optional telemetry alert or circuit breaker.

The distinction between Filtered and Violation is invisible
to the user — in both cases data is simply absent from the
response. The difference is in the audit signal: Filtered is
routine housekeeping, Violation is a security event that may
warrant investigation.

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

### Relationships

```
sh:NodeShape (policy)
    ├── sh:target ──▶ sh:SPARQLTarget
    ├── sh:rule ──▶ sh:SPARQLRule / sh:TripleRule
    ├── sh:condition ──▶ sh:NodeShape
    ├── sh:order ──▶ xsd:decimal
    ├── tg-pol:producesDetermination ──▶ tg-pol:DeterminationType
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

### Storage

Policies are stored in the named graph `urn:graph:policy` within
the same collection as the data they govern. The policy engine
fetches applicable policies at query time by querying this graph
for `sh:NodeShape` instances, filtered by `tg-pol:appliesTo`
against the user context's roles and by `tg-pol:effectiveFrom` /
`tg-pol:effectiveTo` against the current time.

### Ontology

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
    rdfs:comment
        "Application-specific extensions to SHACL-AF for "
        "policy determination, audit, and override tracking. "
        "Policy rules themselves are standard sh:NodeShape "
        "instances with SHACL-AF targets and rules." .

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

tg-pol:Allowed a tg-pol:DeterminationType ;
    rdfs:label "Allowed" ;
    rdfs:comment "Information is fully compliant with policy. Included in response without modification. Standard query log." .

tg-pol:Filtered a tg-pol:DeterminationType ;
    rdfs:label "Filtered" ;
    rdfs:comment "Valid query caught data exceeding user scope (over-retrieval). Matched triples removed silently without trace. Standard policy evaluation audit record." .

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

### Example: Assignment-Based Subject Allowlist

A policy that restricts query results to triples whose subject
matches a resource assigned to the requesting user. This is the
generalised form of the hard-coded demo policy currently in the
codebase. The determination is `Filtered` — this is routine
over-retrieval trimming, not a security event.

```turtle
@prefix tg-pol: <https://trustgraph.ai/ontology/policy/> .
@prefix tg-uc:  <https://trustgraph.ai/ontology/user-context/> .
@prefix sh:     <http://www.w3.org/ns/shacl#> .
@prefix rdfs:   <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd:    <http://www.w3.org/2001/XMLSchema#> .

tg-pol:AssignmentSubjectAllowlist a sh:NodeShape ;
    rdfs:label "Assignment-based subject allowlist" ;
    rdfs:comment
        "When the user has resource assignments, only triples "
        "whose subject IRI matches an assigned resource are "
        "returned. Non-matching triples are filtered as "
        "routine over-retrieval." ;
    tg-pol:producesDetermination tg-pol:Filtered ;
    sh:order 1 ;
    sh:target [
        a sh:SPARQLTarget ;
        sh:select """
            SELECT ?this
            WHERE {
                # Find all triple subjects in the result set
                ?this ?p ?o .

                # The user has at least one assignment
                ?ctx a tg-uc:UserContext ;
                     tg-uc:hasAssignment ?assignment .
                ?assignment tg-uc:resource ?resource .

                # This subject is NOT in the assigned set
                FILTER NOT EXISTS {
                    ?ctx tg-uc:hasAssignment ?a2 .
                    ?a2 tg-uc:resource ?this .
                }
            }
        """
    ] ;
    sh:rule [
        a sh:SPARQLRule ;
        sh:construct """
            CONSTRUCT {
                _:det a tg-pol:PolicyEvaluation ;
                    tg-pol:evaluatedPolicy tg-pol:AssignmentSubjectAllowlist ;
                    tg-pol:evaluatedNode $this ;
                    tg-pol:determination tg-pol:Filtered ;
                    tg-pol:reason "Subject not in user's assigned resources." ;
                    tg-pol:evaluatedAt ?now .
            }
            WHERE {
                BIND(NOW() AS ?now)
            }
        """ ;
        sh:order 1
    ] .
```

### Example: Information Barrier (Chinese Wall)

A policy that blocks access to information associated with the
opposing side of a deal the user is assigned to. Demonstrates
multi-hop graph traversal and negation. The determination is
`Violation` — crossing a Chinese Wall is a security event, not
routine over-retrieval.

```turtle
@prefix tg-pol: <https://trustgraph.ai/ontology/policy/> .
@prefix tg-uc:  <https://trustgraph.ai/ontology/user-context/> .
@prefix sh:     <http://www.w3.org/ns/shacl#> .
@prefix rdfs:   <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd:    <http://www.w3.org/2001/XMLSchema#> .
@prefix ex:     <http://example.org/> .

tg-pol:ChineseWallPolicy a sh:NodeShape ;
    rdfs:label "Chinese wall information barrier" ;
    rdfs:comment
        "Blocks access to deal information when the user is "
        "assigned to the opposing side of the same deal. Does "
        "not fire if the user has clean team status. Produces "
        "a Violation determination — this is a security event." ;
    tg-pol:producesDetermination tg-pol:Violation ;
    sh:order 0 ;
    sh:target [
        a sh:SPARQLTarget ;
        sh:select """
            SELECT ?this
            WHERE {
                # Information node associated with a deal side
                ?this ex:associatedDeal ?deal ;
                      ex:dealSide ?infoSide .

                # User is assigned to the same deal,
                # different side
                ?ctx a tg-uc:UserContext ;
                     tg-uc:hasAssignment ?assignment .
                ?assignment tg-uc:resource ?deal ;
                    tg-uc:scope ?userSide .
                FILTER (?infoSide != ?userSide)

                # No clean team override
                FILTER NOT EXISTS {
                    ?assignment tg-uc:status ex:CleanTeamActive .
                }
            }
        """
    ] ;
    sh:rule [
        a sh:SPARQLRule ;
        sh:construct """
            CONSTRUCT {
                _:det a tg-pol:PolicyEvaluation ;
                    tg-pol:evaluatedPolicy tg-pol:ChineseWallPolicy ;
                    tg-pol:evaluatedNode $this ;
                    tg-pol:determination tg-pol:Violation ;
                    tg-pol:reason "Chinese wall: user is on the opposing side of this deal." ;
                    tg-pol:evaluatedAt ?now .
            }
            WHERE {
                BIND(NOW() AS ?now)
            }
        """ ;
        sh:order 1
    ] .
```

### Example: Role-Based Division Isolation

A policy that restricts visibility to triples within the user's
organisational unit. Demonstrates role-scoped activation using
`tg-pol:appliesTo`. The determination is `Filtered` — an
advisor querying broadly and catching another division's data
is routine over-retrieval, not a security breach.

```turtle
@prefix tg-pol: <https://trustgraph.ai/ontology/policy/> .
@prefix tg-uc:  <https://trustgraph.ai/ontology/user-context/> .
@prefix sh:     <http://www.w3.org/ns/shacl#> .
@prefix rdfs:   <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd:    <http://www.w3.org/2001/XMLSchema#> .
@prefix ex:     <http://example.org/> .

tg-pol:DivisionIsolationPolicy a sh:NodeShape ;
    rdfs:label "Division isolation" ;
    rdfs:comment
        "Filters triples tagged with an organisational unit "
        "that does not match the user's. Only activates for "
        "users with the Advisor role." ;
    tg-pol:producesDetermination tg-pol:Filtered ;
    tg-pol:appliesTo ex:Advisor ;
    sh:order 2 ;
    sh:target [
        a sh:SPARQLTarget ;
        sh:select """
            SELECT ?this
            WHERE {
                # Triple's subject belongs to an org unit
                ?this ex:organisationalUnit ?tripleOrgUnit .

                # User's org unit
                ?ctx a tg-uc:UserContext ;
                     tg-uc:organisationalUnit ?userOrgUnit .

                # Mismatch
                FILTER (?tripleOrgUnit != ?userOrgUnit)
            }
        """
    ] ;
    sh:rule [
        a sh:SPARQLRule ;
        sh:construct """
            CONSTRUCT {
                _:det a tg-pol:PolicyEvaluation ;
                    tg-pol:evaluatedPolicy tg-pol:DivisionIsolationPolicy ;
                    tg-pol:evaluatedNode $this ;
                    tg-pol:determination tg-pol:Filtered ;
                    tg-pol:reason "Triple belongs to a different organisational unit." ;
                    tg-pol:evaluatedAt ?now .
            }
            WHERE {
                BIND(NOW() AS ?now)
            }
        """ ;
        sh:order 1
    ] .
```
