---
layout: default
title: "IAM User Context Provisioning"
parent: "Tech Specs"
---

# IAM User Context Provisioning

## Status

Draft

## Problem Statement

The `UserContext` dataclass provides a rich identity structure
(roles, assignments, entitlements, organisational units, delegation,
purpose) that downstream services such as GraphRAG, policy filtering,
and agent orchestration consume for access-control decisions.

Currently there is no mechanism for the IAM system to populate a
`UserContext`. The gateway validates the JWT and extracts an
`Identity` (user ID and workspace), but this is not translated into
a `UserContext` for downstream services. The fields that
`UserContext` carries — roles, assignments, entitlements,
organisational units — are all information the IAM service holds, but
there is no bridge between the two.

## Options

### Option A: Gateway resolves UserContext at request time

After JWT validation, the gateway calls the IAM service to build a
full `UserContext` and attaches it to every downstream request.

### Option B: Enrich the JWT with UserContext fields

Embed UserContext fields in the JWT claims so the gateway can
construct a `UserContext` locally without an additional service call.

There are two sub-options for how the JWT claims are sourced:

**B1: Derive from IAM user table** — extend the IAM user record with
additional fields (roles, assignments, organisational units, etc.)
and populate the JWT claims from these stored fields at login time.
This requires the IAM service to hold UserContext information that
it does not currently store.

**B2: Caller-supplied at login** — the login event accepts a
UserContext (or its constituent fields) as input, and the IAM
service signs it into the JWT. The signed JWT then serves as a
tamper-proof envelope for the caller-asserted context, which
downstream services can validate against permissions.

## Phase 1: Admin-minted user context tokens

As a pragmatic first step, implement a variant of Option B2: an
admin token-minting endpoint.

A caller authenticated with admin access on a workspace can request
a signed JWT for a specified user identity with a caller-supplied
`UserContext`. This is essentially a sudo operation — the admin
asserts who the user is and what context they carry, and the IAM
service signs it into a JWT that downstream services can trust.

This does not require new IAM storage or per-request service calls.
The trust model is bounded by the admin's authority: only workspace
admins can mint these tokens, so the caller-asserted context is
constrained to workspaces the admin controls.

### Use case

Integration scenarios where the calling system has already
authenticated the user and knows their roles, entitlements, and
organisational context. The calling system uses an admin API key to
mint a short-lived JWT with the appropriate `UserContext`, then
passes that JWT to TrustGraph on behalf of the user.

### Scope

- New IAM operation (e.g. `mint-token`) requiring admin privilege
  on the target workspace
- Accepts: user identity fields and a `UserContext` structure
- Returns: signed JWT containing the `UserContext` in its claims,
  plus standard fields (`iss`, `sub`, `default_workspace`, `iat`,
  `exp`)
- Gateway extracts `UserContext` from validated JWT claims and
  attaches it to downstream requests
- No changes to downstream services — they already consume
  `UserContext`

## Phase 1: Changes Required

- **New IAM operation** (`mint-token` via `POST /api/v1/iam`) —
  accepts a valid admin auth token (JWT or API key) plus a
  `UserContext` payload; returns a new signed JWT with the context
  embedded in its claims
- **New IAM permission** (e.g. `mint-token`) — a workspace-scoped
  permission that authorises the holder to mint tokens for that
  workspace. Must be added to the permission/capability model and
  granted to appropriate roles
- **IAM service** — new `mint-token` operation; validates the
  caller holds the `mint-token` permission on the target workspace,
  then signs the supplied `UserContext` into a JWT
- **Gateway auth** — extract `UserContext` from JWT claims when
  present and attach to downstream requests
- **New CLI** (e.g. `tg-mint-token`) — takes an existing auth
  token and a user context (JSON), calls the mint endpoint,
  outputs the new JWT

## Future Phases

TBD. Use-cases need further exploration. Areas to consider:

- A mechanism for non-admin users to switch between user contexts
  of their own choice (e.g. selecting a role or purpose for a
  session without requiring admin intervention)
- Populating `UserContext` from stored IAM data (Option A or B1)
  for deployments that manage user attributes centrally
- Interaction between caller-supplied context and IAM-derived
  context (merging, overriding, or validating one against the
  other)
