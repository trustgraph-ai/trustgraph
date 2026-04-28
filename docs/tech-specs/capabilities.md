---
layout: default
title: "Capability Vocabulary Technical Specification"
parent: "Tech Specs"
---

# Capability Vocabulary Technical Specification

## Overview

Every gateway endpoint maps to exactly one *capability* — a string
from a closed vocabulary defined in this document.  When the
gateway authorises a request, it hands the IAM regime four things:
the authenticated identity, the required capability, the
operation's resource (the structured identifier of what's being
operated on), and the operation's parameters.  The IAM regime
decides allow or deny; see the [IAM contract](iam-contract.md) for
the full abstraction.

A capability is a **permission**, not a structural classification.
`graph:read` says "the caller may read graphs"; it does not say
where graphs live or how they are addressed.  The shape of a
request — whether workspace appears in the URL, the envelope, or
the body, and whether it is a resource address component or an
operation parameter — is determined by what the operation operates
on, not by what permission it requires.  Permission and structure
are orthogonal; the contract takes both.

This document defines:

- The **capability vocabulary** — the closed list of capability
  strings the gateway uses as input to `authorise`.  All IAM
  regimes share this vocabulary; that's the only schema the
  gateway and the IAM regime have to agree on.
- The **open-source role bundles** — the role-and-scope table the
  OSS IAM regime uses to answer `authorise` calls.  Other regimes
  answer the same call differently; the bundles below are an
  OSS-specific implementation detail, not a contract assertion.

A regime may evaluate `authorise` using role bundles (OSS), IdP
group memberships, attribute-based policies, relationship tuples,
or any other mechanism.  The gateway is unaware of which.  The
capability strings — and the resource component vocabulary the
gateway populates alongside them — are the only thing both sides
have to agree on.

## Motivation

The original IAM spec used hierarchical "minimum role" checks
(`admin` implies `writer` implies `reader`). That shape is simple
but paints the role model into a corner: any enterprise need to
grant a subset of admin abilities (helpdesk that can reset
passwords but not edit flows; analyst who can query but not ingest)
requires a protocol-level change.

A capability vocabulary decouples "what a request needs" from
"what roles a user has" and makes the role table pure data. The
open-source bundles can stay coarse while the enterprise role
table expands without any code movement.

## Design

### Capability string format

`<subsystem>:<verb>` or `<subsystem>` (for capabilities with no
natural read/write split). All lowercase, kebab-case for
multi-word subsystems.

### Capability list

**Data plane**

| Capability | Covers |
|---|---|
| `agent` | agent (query-only; no write counterpart) |
| `graph:read` | graph-rag, graph-embeddings-query, triples-query, sparql, graph-embeddings-export, triples-export |
| `graph:write` | triples-import, graph-embeddings-import |
| `documents:read` | document-rag, document-embeddings-query, document-embeddings-export, entity-contexts-export, document-stream-export, library list / fetch |
| `documents:write` | document-embeddings-import, entity-contexts-import, text-load, document-load, library add / replace / delete |
| `rows:read` | rows-query, row-embeddings-query, nlp-query, structured-query, structured-diag |
| `rows:write` | rows-import |
| `llm` | text-completion, prompt (stateless invocation) |
| `embeddings` | Raw text-embedding service (stateless compute; typed-data embedding stores live under their data-subject capability) |
| `mcp` | mcp-tool |
| `collections:read` | List / describe collections |
| `collections:write` | Create / delete collections |
| `knowledge:read` | List / get knowledge cores |
| `knowledge:write` | Create / delete knowledge cores |

**Control plane**

| Capability | Covers |
|---|---|
| `config:read` | Read workspace config |
| `config:write` | Write workspace config |
| `flows:read` | List / describe flows, blueprints, flow classes |
| `flows:write` | Start / stop / update flows |
| `users:read` | List / get users within the workspace |
| `users:write` | Create / update / disable users within the workspace |
| `users:admin` | Assign / remove roles on users within the workspace |
| `keys:self` | Create / revoke / list **own** API keys |
| `keys:admin` | Create / revoke / list **any user's** API keys within the workspace |
| `workspaces:admin` | Create / delete / disable workspaces (system-level) |
| `iam:admin` | JWT signing-key rotation, IAM-level operations |
| `metrics:read` | Prometheus metrics proxy |

### Open-source role bundles

The open-source edition ships three roles:

| Role | Capabilities |
|---|---|
| `reader` | `agent`, `graph:read`, `documents:read`, `rows:read`, `llm`, `embeddings`, `mcp`, `collections:read`, `knowledge:read`, `flows:read`, `config:read`, `keys:self` |
| `writer` | everything in `reader` **+** `graph:write`, `documents:write`, `rows:write`, `collections:write`, `knowledge:write` |
| `admin` | everything in `writer` **+** `config:write`, `flows:write`, `users:read`, `users:write`, `users:admin`, `keys:admin`, `workspaces:admin`, `iam:admin`, `metrics:read` |

Open-source bundles are deliberately coarse. `workspaces:admin` and
`iam:admin` live inside `admin` without a separate role; a single
`admin` user holds the keys to the whole deployment.

### The `agent` capability and composition

The `agent` capability is granted independently of the capabilities
it composes under the hood (`llm`, `graph`, `documents`, `rows`,
`mcp`, etc.). A user holding `agent` but not `llm` can still cause
LLM invocations because the agent implementation chooses which
services to invoke on the caller's behalf.

This is deliberate. A common policy is "allow controlled access
via the agent, deny raw model calls" — granting `agent` without
granting `llm` expresses exactly that. An administrator granting
`agent` should treat it as a grant of everything the agent
composes at deployment time.

### Authorisation evaluation (OSS regime)

This section describes how the OSS IAM regime answers
`authorise(identity, capability, resource, parameters)`.  Other
regimes answer the same contract differently; only the inputs (the
capability vocabulary, the resource components, the parameter
shape) are shared.

For a request bearing a resolved set of roles
`R = {r1, r2, ...}`, a required capability `c`, a resource, and
parameters:

```
let target_workspace =
        resource.workspace                  (workspace-/flow-level resources)
        or parameters.workspace             (system-level resources whose
                                             parameters reference a workspace)
        or unset                            (system-level operations with no
                                             workspace context)

allow if some role r in R has c in its capability bundle
        and (target_workspace is unset
             or r's workspace_scope permits target_workspace)
```

The OSS regime considers workspace from whichever role it plays in
the operation:

- For workspace-level and flow-level resources, the workspace lives
  in `resource.workspace` and that is what the role's scope is
  checked against.
- For system-level resources whose operation parameters reference a
  workspace (e.g. `create-user with workspace association W`),
  workspace lives in `parameters.workspace` and that is what the
  role's scope is checked against.  The resource is system-level
  (`resource = {}`) but the workspace constraint still bites.
- For system-level operations with no workspace context (e.g.
  `bootstrap`, `rotate-signing-key`), the workspace-scope check
  collapses — only capability-bundle membership matters.

No hierarchy, no precedence, no role-order sensitivity.  A user
with a single role is the common case; a user with multiple roles
is allowed if any role independently grants both the capability
and the relevant workspace scope.

### Enforcement boundary

Capability checks — and authentication — are applied **only at the
API gateway**, on requests arriving from external callers.
Operations originating inside the platform (backend service to
backend service, agent to LLM, flow-svc to config-svc, bootstrap
initialisers, scheduled reconcilers, autonomous flow steps) are
**not capability-checked**. Backend services trust the workspace
set by the gateway on inbound pub/sub messages and trust
internally-originated messages without further authorisation.

This policy has four consequences that are part of the spec, not
accidents of implementation:

1. **The gateway is the single trust boundary for user
   authorisation.** Every backend service is a downstream consumer
   of an already-authorised workspace scope.
2. **Pub/sub carries workspace, not user identity.** Messages on
   the bus do not carry credentials or the identity that originated
   a request; they carry the resolved workspace only. This keeps
   the bus protocol free of secrets and aligns with the workspace
   resolver's role as the gateway-side narrowing step.
3. **Composition is transitive.** Granting a capability that the
   platform composes internally (for example, `agent`) transitively
   grants everything that capability composes under the hood,
   because the downstream calls are internal-origin and are not
   re-checked. The composite nature of `agent` described above is
   a consequence of this policy, not a special case.
4. **Internal-origin operations have no user.** Bootstrap,
   reconcilers, and other platform-initiated work act with
   system-level authority. The workspace field on such messages
   identifies which workspace's data is being touched, not who
   asked.

**Trust model.** Whoever has pub/sub access is implicitly trusted
to act as any workspace. Defense-in-depth within the backend is
not part of this design; the security perimeter is the gateway
and the bus itself (TLS / network isolation between the bus and
any untrusted network).

### Unknown capabilities and unknown roles

- An endpoint declaring an unknown capability is a server-side bug
  and fails closed (403, logged).
- A user carrying a role name that is not defined in the role table
  is ignored for authorisation purposes and logged as a warning.
  Behaviour is deterministic: unknown roles contribute zero
  capabilities.

### Capability scope

Every capability is **implicitly scoped to the caller's resolved
workspace**. A `users:write` capability does not permit a user
in workspace `acme` to create users in workspace `beta` — the
workspace-resolver has already narrowed the request to one
workspace before the capability check runs. See the IAM
specification for the workspace-resolver contract.

The three exceptions are the system-level capabilities
`workspaces:admin` and `iam:admin`, which operate across
workspaces by definition, and `metrics:read`, which returns
process-level series not scoped to any workspace.

## Enterprise extensibility

Enterprise editions extend the role table additively:

```
data-analyst:   {query, library:read, collections:read, knowledge:read}
helpdesk:       {users:read, users:write, users:admin, keys:admin}
data-engineer:  writer + {flows:read, config:read}
workspace-owner: admin − {workspaces:admin, iam:admin}
```

None of this requires a protocol change — the wire-protocol `roles`
field on user records is already a set, the gateway's
capability-check is already capability-based, and the capability
vocabulary is closed. Enterprises may introduce roles whose bundles
compose the same capabilities differently.

When an enterprise introduces a new capability (e.g. for a feature
that does not exist in open source), the capability string is
added to the vocabulary and recognised by the gateway build that
ships that feature.

## References

- [IAM Contract Specification](iam-contract.md) — the abstract
  gateway↔IAM regime contract; capability strings are inputs to
  `authorise`.
- [Identity and Access Management Specification](iam.md)
- [IAM Service Protocol Specification](iam-protocol.md) — the OSS
  regime's wire-level protocol.
- [Architecture Principles](architecture-principles.md)
