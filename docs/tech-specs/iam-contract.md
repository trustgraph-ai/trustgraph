---
layout: default
title: "IAM Contract Technical Specification"
parent: "Tech Specs"
---

# IAM Contract Technical Specification

## Overview

The IAM contract is the abstraction between the API gateway and any
identity / access management regime that fronts it.  The gateway
treats IAM as a black box behind two operations — *authenticate* and
*authorise* — plus a small surface of management operations.  No
regime-specific concept (roles, scopes, groups, claims, policy
languages) is visible to the gateway, and no gateway-specific
concept (capability vocabulary, request anatomy) is visible to
backend services.

The TrustGraph open-source distribution ships one IAM regime — a
role-based implementation defined in
[`iam-protocol.md`](iam-protocol.md) — that is one implementation of
this contract.  Enterprise editions can replace it with a different
regime (OIDC / SSO, ABAC, ReBAC, external policy engine) without
changing the gateway, the wire protocol, or the backends.

## Motivation

Authorisation models vary by deployment.  A small team might be
happy with three predefined roles; an enterprise might need group-
mapping from an upstream IdP, attribute-based policies, or
relationship-based access control.  Hard-wiring any one of those
into the gateway forces every other regime to either compromise its
model or be re-implemented.

A narrow contract — "authenticate this credential" and "may this
identity perform this operation on this resource" — captures what
the gateway actually needs to know without committing to a policy
shape.  The IAM regime owns the policy decision; the gateway is a
generic enforcement point.

## Operations

### `authenticate`

```
authenticate(credential: bytes) → Identity | AuthFailure
```

Validates a credential the client presented.  The gateway treats
the credential as opaque bytes — for the OSS regime today that's
either an API key plaintext or a JWT, but the gateway does not
parse them; the IAM regime decides.

On success, returns an `Identity`.  On any failure the IAM regime
returns the same opaque `AuthFailure` — never a description of which
condition failed.  This is the spec's masked-error rule: an
attacker probing the endpoint cannot distinguish "no such key",
"expired", "wrong signature", "revoked", "user disabled", etc.

### `authorise`

```
authorise(identity: Identity,
          capability: str,
          resource: Resource,
          parameters: dict)
    → Decision
```

Asks whether the identity is permitted to perform the named
capability on the named resource, given the operation's
parameters.  Returns `allow` or `deny`.  `identity` is whatever
`authenticate` returned for this caller; the gateway never
decomposes it.

The four arguments separate concerns:

- **`identity`** — who is asking.
- **`capability`** — what permission they are exercising (e.g.
  `users:write`, `graph:read`).  Permission, not structure.
- **`resource`** — what is being operated on, as a structured
  identifier.  See *The Resource model* below.
- **`parameters`** — operation-specific data that the regime may
  need to consider beyond the resource identifier.  Used when a
  decision depends on attributes the request supplies — e.g. an
  admin scoped to one workspace creating a user *with workspace
  association W*: the resource is the system-level user registry,
  and W is a parameter the regime checks against the admin's
  scope.

Different regimes use the four arguments differently — the OSS
regime checks role bundles against the capability and the role's
workspace scope against parameters; an SSO regime might consult an
upstream IdP's group memberships; an ABAC regime evaluates a
policy with all four as inputs.  The contract is unchanged.

### `authorise_many`

```
authorise_many(identity: Identity,
               checks: list[(str, Resource, dict)])
    → list[Decision]
```

Bulk variant of `authorise`.  Same semantics, one round-trip for
many decisions.  Used when an operation fans out to multiple
resources (e.g. an agent that touches several workspaces) and a
single permission check isn't sufficient.

`authorise_many` is not just a performance optimisation; it pins
the contract for fan-out operations early, before clients (or
internal callers) build patterns that assume one-permission-check-
per-request.  Regimes implement it as a loop over `authorise`
unless they have a more efficient path.

### Management operations

Beyond the request-time `authenticate` / `authorise`, the contract
also covers identity-lifecycle and credential-lifecycle operations
that are invoked by administrative requests rather than by the
authentication path.  These are regime-specific in detail (an SSO
regime that delegates user management to the IdP may not implement
most of them) but the operation set the gateway can forward is:

- User management: `create-user`, `list-users`, `get-user`,
  `update-user`, `disable-user`, `enable-user`, `delete-user`
- Credential management: `create-api-key`, `list-api-keys`,
  `revoke-api-key`, `change-password`, `reset-password`
- Workspace management: `create-workspace`, `list-workspaces`,
  `get-workspace`, `update-workspace`, `disable-workspace`
- Session management: `login`
- Key management: `get-signing-key-public`, `rotate-signing-key`
- Bootstrap: `bootstrap`

A regime that does not support one of these (e.g. an SSO regime
where users are managed in the IdP) returns a defined "not
supported" error; the gateway surfaces it as a 501.

## The `Identity` surface

`Identity` is *mostly* opaque.  The gateway holds the value as a
token to quote back when calling `authorise`, never decomposing it.
But there are a few gateway-side concerns that need a small
surface:

| Field | Purpose |
|---|---|
| `handle` | Opaque reference passed back to `authorise`.  Regime-defined; gateway treats as a string. |
| `workspace` | The workspace this credential authenticates to.  Used by the gateway only as a default-fill-in for operations that omit a workspace.  Never used as policy input — when authorisation needs to know which workspace the operation acts on, the operation places it in the resource address (or a parameter), and the regime decides. |
| `principal_id` | Stable identifier the gateway logs for audit (a user id, a sub claim, a service account id).  Never used for authorisation — that's `authorise`'s job. |
| `source` | How the credential was presented (`api-key`, `jwt`, …).  Non-policy; useful for logs and metrics only. |

Anything else — roles, claims, group memberships, policy attributes
— stays inside the regime and is reachable only via `authorise`.

## The `Resource` model

A `Resource` is a structured value identifying *what is being
operated on*.  Resources live at one of three levels in TrustGraph,
based on where the resource exists in the deployment:

### Resource levels

| Level | What lives there | Resource shape |
|---|---|---|
| **System** | The user registry, the workspace registry, the signing key, the audit log — anything that exists once per deployment. | `{}` |
| **Workspace** | A workspace's config, flow definitions, library (documents), knowledge cores, collections — things that exist *within* a workspace. | `{workspace: "..."}` |
| **Flow** | A flow's knowledge graph, agent state, LLM context, embedding state, MCP context — things that exist *within* a flow within a workspace. | `{workspace: "...", flow: "..."}` |

Note carefully:

- **Users are a system-level resource.**  A user record exists at
  the deployment level; the fact that a user has a *workspace
  association* (one in OSS, possibly many in other regimes) is a
  property of the user record, not a containment.  Operations on
  the user registry have `resource = {}`; the workspace
  association appears as a *parameter*, not as a resource address
  component.
- **Workspaces themselves are a system-level resource.** The
  workspace registry exists at the deployment level.  `create-
  workspace` and `list-workspaces` are system-level operations;
  the workspace identifier in their bodies is a parameter, not an
  address.
- **A workspace's contents are workspace-level resources.**  A
  workspace's config, flows, library, etc. live within a
  workspace.  Their resource address is `{workspace: ...}`.
- **A flow's contents are flow-level resources.**  Knowledge
  graphs, agents, etc. live within a flow.  Their resource
  address is `{workspace: ..., flow: ...}`.

### Component vocabulary

| Component | Type | Meaning | Used by |
|---|---|---|---|
| `workspace` | string | Identifier of the workspace whose contents are being operated on | workspace-level and flow-level resource addresses |
| `flow` | string | Identifier of a flow within a workspace; always paired with `workspace` | flow-level resource addresses |
| `collection` | string | Reserved for finer-grained scoping within a workspace | future / enterprise |
| `document` | string | Reserved for per-document scoping | future / enterprise |

A `Resource` is a partial mapping of these components to values.
The level of the resource (system / workspace / flow) determines
which components must be present.  An empty `{}` is the
system-level resource.

### Workspace as parameter vs. address

Workspace plays two distinct roles in operations and shows up in
two distinct places:

- **As a resource address component** — workspace identifies the
  thing being operated on.  Lives in `resource.workspace`.  Example:
  `config:read` reads the config *of* workspace W.
- **As an operation parameter** — workspace is data the operation
  acts on or filters by, while the resource itself is system-level.
  Lives in `parameters.workspace`.  Example: `users:write`
  creates a user *with workspace association* W; the resource is
  the user registry (system), and W is a parameter.

These are not interchangeable.  The IAM regime considers each role
separately; the OSS role table, for instance, applies workspace-
scope to the address component when checking workspace-level
operations, and to a parameter when checking
"create-user-with-workspace-W".  Both end up enforcing the admin's
scope, but through different code paths.

### Extension rules

The vocabulary is closed but extensible.  Adding a new component:

1. The component is added to the vocabulary in this spec, with a
   defined name, type, and meaning.
2. Existing IAM regimes ignore unknown components (forward
   compatibility — adding a new component does not break older
   regimes that don't understand it).
3. Older gateways that don't populate a new component leave it
   unset; regimes that need it for a decision treat "unset" as
   "absent" and decide accordingly (typically: cannot grant
   permission scoped to a component the gateway didn't supply).

A regime that wants stricter behaviour (e.g. fail-closed on
unknown components rather than ignoring them) declares so as part
of its own configuration; the contract default is "ignore unknown".

## Operation registry (gateway-side)

Mapping a request onto `(capability, resource, parameters)` is
service-specific — it cannot be inferred from the capability
alone.  The gateway maintains an **operation registry** that
declares, per operation:

- The required capability.
- The resource level (system / workspace / flow) — determines the
  shape of the resource identifier.
- How to extract the resource address components (workspace,
  flow) from the request — from URL path, WebSocket envelope, or
  body.
- Which body fields are operation parameters (and which of those
  the IAM regime should see in the `parameters` argument).

This registry is part of the gateway's endpoint declarations, not
part of the IAM contract.  The contract specifies what arguments
`authorise` receives; how the gateway populates them is its own
concern.

In the OSS gateway, registry keys follow these conventions:

| Pattern | Used by | Resource level |
|---|---|---|
| bare op name (`create-user`, `list-users`, `login`, …) | `/api/v1/iam` and the auth surface | system / workspace, per op |
| `<kind>:<op>` (`config:get`, `flow:list-blueprints`, `librarian:add-document`, …) | `/api/v1/{kind}` (workspace-scoped global services) | workspace |
| `flow-service:<kind>` (`flow-service:agent`, `flow-service:graph-rag`, …) | `/api/v1/flow/{flow}/service/{kind}` and the WS Mux | flow |
| `flow-import:<kind>` / `flow-export:<kind>` | `/api/v1/flow/{flow}/{import,export}/{kind}` streaming sockets | flow |

Keys are an OSS-gateway implementation detail — the contract does
not constrain naming.  The conventions above exist so the registry
key is uniquely derivable from the request path and (where
applicable) body without ambiguity.

## Caching

Both `authenticate` and `authorise` results are cached at the
gateway, on different policies:

- **`authenticate`** — cached by a hash of the credential.  The OSS
  gateway uses a fixed short TTL (currently 60 s) so that revoked
  API keys and disabled users stop working within the TTL window
  without any push mechanism.  Regimes that want a different
  behaviour can return an `expires` hint with the identity; the
  gateway honours the smaller of `expires` and its own ceiling.

- **`authorise`** — cached by a hash of `(handle, capability,
  resource, parameters)`.  The regime returns a suggested TTL with
  the decision; the gateway clamps it above by a deployment-set
  ceiling (currently 60 s).  Both allow and deny decisions are
  cached; denies briefly, to avoid hammering the regime with
  repeated rejected attempts.

The TTL ceiling caps the revocation latency window — a role
revoked at the regime takes effect at the gateway no later than
the ceiling.  Operators that need stricter revocation can lower
the ceiling.

## Failure modes

| Condition | Behaviour |
|---|---|
| `authenticate` returns AuthFailure | Gateway responds 401 with the masked `auth failure` body. |
| `authorise` returns deny | Gateway responds 403 with the masked `access denied` body. |
| IAM regime unreachable | Gateway responds 401 / 503 (deployment-defined).  No fail-open. |
| `authorise_many` partial deny | Gateway treats the request as denied; the operation is rejected.  Partial-success semantics are not part of the contract. |
| Regime returns "not supported" for a management operation | Gateway responds 501. |

There is no fallback or "soft" decision path.  An IAM regime that
is unavailable, slow, or returning errors causes requests to fail
closed.

## Implementations

### Open-source role-based regime

Defined in [`iam-protocol.md`](iam-protocol.md).  Implements the
contract via:

- A pub/sub request/response service (`iam-svc`) reached only by
  the gateway over the message bus.
- Credentials are API keys (opaque) or JWTs (Ed25519, locally
  validated by the gateway against the regime's published public
  key).
- `authorise` reduces to a role-and-workspace-scope check against
  the role table defined in [`capabilities.md`](capabilities.md).
- Identity, user, and workspace records live in Cassandra.

The OSS regime is deliberately simple — three roles, single
home-workspace per user (a regime data-model decision, not a
contract assertion), no policy language.

### Future regimes

The contract is shaped to admit, without code change in the
gateway:

- **OIDC / SSO** — `authenticate` validates an OIDC ID token via
  the IdP's JWKS; `Identity.handle` carries the verified subject
  and group claims; `authorise` evaluates against group-to-
  capability mappings configured at the regime.
- **ABAC / Policy engine** — `authorise` calls out to a policy
  engine (Rego, Cedar, custom DSL) with the identity's attributes
  and the resource as the policy input.
- **ReBAC (Zanzibar-style)** — `authorise` translates `(identity,
  capability, resource)` into a relationship-tuple lookup against
  a tuple store.
- **Hybrid** — multiple regimes composed: e.g. authenticate via
  SSO, authorise via local policy.

None of these require gateway changes.  The contract surface is
the same; the regime is what differs.

## References

- [Identity and Access Management Specification](iam.md) — overall
  design and the gateway-side framing.
- [IAM Service Protocol Specification](iam-protocol.md) — the OSS
  regime's wire-level protocol.
- [Capability Vocabulary Specification](capabilities.md) — the
  capability strings the gateway uses as `authorise` input.
