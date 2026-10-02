---
layout: default
title: "Policy Examples"
parent: "Tech Specs"
---

# Policy Examples

Worked examples of SHACL-AF policy shapes demonstrating different
access control patterns. Each example includes the SPARQL target
(which nodes match) and a CONSTRUCT rule (which produces an
`sh:ValidationResult` with the determination, reason, and
blocking behaviour).

See also:
- [Policy Filtering Overview](policy-filtering.md) — problem
  statement and SHACL-AF rationale
- [Policy Ontology](policy-ontology.md) — vocabulary and
  determination types
- [Bletchley Park test dataset](policy-test-data/bletchley-README.md)
  — a complete working dataset with policies and personas
- [AeroSentinel test dataset](policy-test-data/README.md)
  — a second test dataset with commercial/defense separation

## Assignment-Based Subject Allowlist

A policy that restricts query results to triples whose subject
matches a resource assigned to the requesting user. This is the
generalised form of the hard-coded demo policy currently in the
codebase. The determination is `tg-pol:Filtered` — this is
routine over-retrieval trimming, not a security event.

```turtle
@prefix tg-pol: <https://trustgraph.ai/ontology/policy/> .
@prefix tg-uc:  <https://trustgraph.ai/ontology/user-context/> .
@prefix sh:     <http://www.w3.org/ns/shacl#> .
@prefix rdfs:   <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd:    <http://www.w3.org/2001/XMLSchema#> .

tg-pol:AssignmentSubjectAllowlist a sh:NodeShape ;
    rdfs:label "Assignment-based subject allowlist" ;
    rdfs:comment "When the user has resource assignments, only triples whose subject IRI matches an assigned resource are returned. Non-matching triples are filtered as routine over-retrieval." ;
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
                _:result a sh:ValidationResult ;
                    sh:focusNode $this ;
                    sh:sourceShape tg-pol:AssignmentSubjectAllowlist ;
                    sh:resultSeverity tg-pol:Filtered ;
                    sh:resultMessage "Subject not in user's assigned resources." ;
                    tg-pol:blocks true .
            }
            WHERE { }
        """ ;
        sh:order 1
    ] .
```

## Information Barrier (Chinese Wall)

A policy that blocks access to information associated with the
opposing side of a deal the user is assigned to. Demonstrates
multi-hop graph traversal and negation. The determination is
`tg-pol:Violation` — crossing a Chinese Wall is a security
event, not routine over-retrieval.

```turtle
@prefix tg-pol: <https://trustgraph.ai/ontology/policy/> .
@prefix tg-uc:  <https://trustgraph.ai/ontology/user-context/> .
@prefix sh:     <http://www.w3.org/ns/shacl#> .
@prefix rdfs:   <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd:    <http://www.w3.org/2001/XMLSchema#> .
@prefix ex:     <http://example.org/> .

tg-pol:ChineseWallPolicy a sh:NodeShape ;
    rdfs:label "Chinese wall information barrier" ;
    rdfs:comment "Blocks access to deal information when the user is assigned to the opposing side of the same deal. Does not fire if the user has clean team status. Produces a Violation determination — this is a security event." ;
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
                _:result a sh:ValidationResult ;
                    sh:focusNode $this ;
                    sh:sourceShape tg-pol:ChineseWallPolicy ;
                    sh:resultSeverity tg-pol:Violation ;
                    sh:resultMessage "Chinese wall: user is on the opposing side of this deal." ;
                    tg-pol:blocks true .
            }
            WHERE { }
        """ ;
        sh:order 1
    ] .
```

## Role-Based Division Isolation

A policy that restricts visibility to triples within the user's
organisational unit. Demonstrates role-scoped activation using
`tg-pol:appliesTo`. The determination is `tg-pol:Filtered` — an
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
    rdfs:comment "Filters triples tagged with an organisational unit that does not match the user's. Only activates for users with the Advisor role." ;
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
                _:result a sh:ValidationResult ;
                    sh:focusNode $this ;
                    sh:sourceShape tg-pol:DivisionIsolationPolicy ;
                    sh:resultSeverity tg-pol:Filtered ;
                    sh:resultMessage "Triple belongs to a different organisational unit." ;
                    tg-pol:blocks true .
            }
            WHERE { }
        """ ;
        sh:order 1
    ] .
```

## Non-Blocking Access Logging

A policy that logs access to sensitive-but-permitted data
without restricting it. Demonstrates `tg-pol:blocks false` —
the data passes through, but a policy event is emitted for
audit purposes.

```turtle
@prefix tg-pol: <https://trustgraph.ai/ontology/policy/> .
@prefix tg-uc:  <https://trustgraph.ai/ontology/user-context/> .
@prefix sh:     <http://www.w3.org/ns/shacl#> .
@prefix rdfs:   <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd:    <http://www.w3.org/2001/XMLSchema#> .
@prefix ex:     <http://example.org/> .

tg-pol:SensitiveAccessLog a sh:NodeShape ;
    rdfs:label "Sensitive data access log" ;
    rdfs:comment "Logs access to data marked as sensitive. Does not block — the user is authorised, but the access is recorded." ;
    sh:order 10 ;
    sh:target [
        a sh:SPARQLTarget ;
        sh:select """
            SELECT ?this
            WHERE {
                ?this ex:sensitivity ex:High .
            }
        """
    ] ;
    sh:rule [
        a sh:SPARQLRule ;
        sh:construct """
            CONSTRUCT {
                _:result a sh:ValidationResult ;
                    sh:focusNode $this ;
                    sh:sourceShape tg-pol:SensitiveAccessLog ;
                    sh:resultSeverity tg-pol:SensitiveAccess ;
                    sh:resultMessage "Access to high-sensitivity data recorded." ;
                    tg-pol:blocks false .
            }
            WHERE { }
        """ ;
        sh:order 1
    ] .
```
