---
layout: default
title: "User Context Technical Specification"
parent: "Tech Specs"
---

# User Context Technical Specification

## Overview

This specification describes a general-purpose user context data
structure that captures who is querying the knowledge graph — their
roles, resource assignments, entitlements, organisational position,
and override authority — so that policy rules can evaluate access
scope and determine what data is visible, blocked, or minimised.

## Problem Statement

Knowledge graph queries currently execute without identity context.
Every query sees the same data regardless of who is asking. In
real-world deployments, different users need different views of the
same graph:

- A wealth advisor should see their assigned clients' portfolios but
  not other clients'.
- A deal team member on the buy side should not see sell-side
  intelligence for the same deal.
- A trust beneficiary should see their own branch but not sibling
  branches.
- A compliance officer needs broad read access for audit, but only
  within compliance functions.

These access decisions depend on the user's identity, roles, resource
assignments, and organisational position — none of which are available
at query time today. Without this context, policy enforcement is
impossible and all data is either fully open or fully locked.

## Vision

The user context is a transient data structure assembled at query time
and discarded after the query completes. It is not persisted in the
knowledge graph. It is injected as an ephemeral named graph so that
policy rules can reference it using the same query mechanisms
(SPARQL, graph traversal) used for the rest of the knowledge graph.

The data structure is domain-agnostic. Domain-specific ontologies
extend it with concrete roles, assignment types, and entitlements.
The general structure defines seven core concepts:

### Role

What hat the user is wearing, which activates different policy rules.
A user may hold multiple roles. The role determines which policies
fire and what graph scope is visible.

Example: "Advisor", "Customer", "Auditor", "Admin". In healthcare,
"Treating Physician", "Nurse", "Patient". In legal, "Partner",
"Associate", "Client".

### Assignment

A scoped grant tying a user to a specific resource with qualifiers.
An assignment says "this user is connected to this thing, in this
capacity, with this status." Assignments imply responsibility — the
user is actively working on or managing the resource.

Assignments carry temporal validity (`validFrom`, `validTo`) so that
time-based access is evaluated within the context graph rather than
in external logic.

Example: a doctor assigned to a patient (resource = patient,
scope = treating physician, status = active, validTo = end of shift).
A deal team member assigned to a deal (resource = deal,
scope = buy side, status = clean team active,
validTo = deal close date).

### Entitlement

A grant to view a specific resource scope. Similar to an assignment
but carries different semantics: an assignment implies responsibility
("you're working on this"), an entitlement implies visibility
("you're allowed to see this"). Policy rules can distinguish between
the two.

Like assignments, entitlements carry `validFrom` and `validTo` for
temporal scoping.

Example: a trust beneficiary entitled to view Trust Branch A but not
Trust Branch B. A SaaS user entitled to view the Enterprise Analytics
dashboard until their trial expires.

### Organisational Unit

Where the user sits in the organisational structure. Used for
division-level isolation so that one part of the organisation cannot
see another's data.

Example: "Engineering", "Legal", "Trading Floor". In healthcare,
"Cardiology", "Emergency", "Pharmacy".

### Override Authority

Permission to bypass a specific policy under stated conditions.
Overrides are scoped to named policy areas and carry conditions that
must be met. This keeps overrides auditable and prevents ad-hoc
privilege escalation.

Example: a compliance officer can override a Chinese Wall restriction
with written justification and elevated audit logging. A doctor can
break the glass on a restricted patient record in an emergency, with
the access logged and reviewed.

### Delegation

Represents one user acting on behalf of another. The logged-in user
(the delegate) exercises the authority of another user or entity
(the delegator) within a defined scope. This covers assistants,
power-of-attorney, supervised trainees, and similar multi-party
relationships.

Policy rules see both the primary subject (who is logged in) and
the effective subject (whose authority is being exercised), allowing
fine-grained control over delegated actions.

Example: a personal assistant submitting a trade on behalf of a
portfolio manager. A trainee doctor accessing patient records under
the supervision of an attending physician.

### Purpose

A declaration of why the query is being made. Purpose is not
typically used for primary access decisions but provides supporting
context for edge cases — particularly where regulatory frameworks
(GDPR, HIPAA, CCPA) require that access depends not just on who is
asking but why.

Purpose is a single field on the query context. It is carried
through to audit logs so that access patterns can be reviewed
against stated intent.

Example: "ClientServicing", "AuditLogReview", "Research". An advisor
might have access to client data for servicing but be blocked if the
purpose is marketing outreach without explicit consent.

## Domain Specialisation

The general user context is not used directly. Domain ontologies
import it and define concrete roles, assignment types, and
entitlements. For example, a wealth banking domain ontology would
define:

- Roles: Customer, WealthAdvisor, PortfolioManager, DealTeamMember,
  Trustee, Beneficiary, ComplianceOfficer
- Assignments: DealAssignment (with side designation and clean team
  status)
- Entitlements: BranchEntitlement (with entitled branch reference)
- Organisational units: WealthManagement, InvestmentBanking,
  CommercialBanking, Compliance
- Override authorities: policy area and condition for compliance
  overrides
- Delegations: assistant acting on behalf of a portfolio manager,
  with scope limited to trade submission
- Purposes: ClientServicing, DealExecution, ComplianceReview

The general structure provides the vocabulary; the domain ontology
provides the instances.

## Data Model

Schema definitions in `trustgraph-base/trustgraph/schema/`. These
are the general-purpose primitives; domain ontologies compose them
to build concrete user contexts.

```python
from dataclasses import dataclass, field

@dataclass
class Assignment:
    resource: str = ""
    scope: str = ""
    status: str = ""
    valid_from: str = ""
    valid_to: str = ""
    qualifiers: dict[str, str] = field(default_factory=dict)

@dataclass
class Entitlement:
    resource_scope: str = ""
    access_level: str = ""
    valid_from: str = ""
    valid_to: str = ""

@dataclass
class OverrideAuthority:
    policy_area: str = ""
    condition: str = ""

@dataclass
class Delegation:
    delegator_id: str = ""
    scope: str = ""

@dataclass
class UserContext:
    user_id: str = ""
    roles: list[str] = field(default_factory=list)
    assignments: list[Assignment] = field(default_factory=list)
    entitlements: list[Entitlement] = field(default_factory=list)
    organisational_units: list[str] = field(default_factory=list)
    override_authorities: list[OverrideAuthority] = field(default_factory=list)
    delegation: Delegation | None = None
    purpose: str = ""
```

**Field notes:**

- All identity and classification fields (`user_id`, `roles`,
  `resource`, `scope`, `resource_scope`, `access_level`,
  `policy_area`, `delegator_id`, `organisational_unit`) are IRIs.
  This is an RDF graph — roles, resources, and scopes are identified
  by IRI so that policy rules can reference them in SPARQL and
  domain ontologies can define hierarchies via `rdfs:subClassOf`.
- `Assignment.qualifiers` — open-ended IRI-keyed pairs for
  domain-specific qualifiers (e.g. `{"wb:sideDesignation": "wb:BuySide",
  "wb:cleanTeamStatus": "wb:Active"}` in banking).
- `Delegation.delegator_id` — the user whose authority is being
  exercised. When present, `user_id` is the delegate (logged-in
  user) and `delegator_id` is the effective subject.
- `purpose` — IRI identifying the purpose. Carried to audit logs.
  Not parsed by the policy engine unless a domain policy explicitly
  references it.
- `condition` — free-text description of override conditions.
- `valid_from` / `valid_to` — ISO 8601 datetime strings. Empty
  means unbounded.

## Design Decisions

- **Context population**: User context will be populated through
  RBAC. The exact mechanism is TBD and out of scope for this
  specification. The immediate use case is early validation of
  policy rules.
- **Hierarchical roles**: Supported implicitly through role types.
  Domain ontologies can define role hierarchies using
  `rdfs:subClassOf` relationships between role classes, and policy
  rules can match at any level of the hierarchy.
- **Workspace interaction**: User context and workspace isolation
  are orthogonal. Workspaces scope the data; user context scopes
  visibility within a workspace. The primary purpose of user
  context is to determine what gets retrieved from the graph at
  query time, interacting with policy rules to filter results.

## Open Questions

- How does user context interact with the policy engine at query
  time — is it evaluated as SPARQL constraints, as post-retrieval
  filters, or both?
- What is the minimal viable context needed for the first policy
  validation use cases?
