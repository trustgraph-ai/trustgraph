---
layout: default
title: "No-Auth IAM Regime"
parent: "Tech Specs"
---

# No-Auth IAM Regime

## Overview

A minimal IAM regime that permits all access unconditionally.
Implements the same Pulsar request/response protocol as `iam-svc`
(see [iam-contract.md](iam-contract.md)) so it is a drop-in
replacement: swap `iam-svc` for `no-auth-svc` in the deployment
and the gateway, bootstrapper, and all other components continue
to work without modification.

Intended for development, testing, single-tenant self-hosted
deployments, and evaluation environments where authentication
overhead is unwanted.

## Motivation

The full IAM regime requires Cassandra tables, a bootstrap
sequence, API key management, and signing key rotation.  For
many deployments this is unnecessary friction:

- Local development and CI/CD pipelines.
- Single-user or small-team self-hosted instances.
- Evaluation and demo environments.
- Deployments behind an external authentication proxy
  (e.g. OAuth2 reverse proxy, VPN-gated access).

Today operators who want no auth must still deploy `iam-svc` and
complete the bootstrap ceremony.  A purpose-built no-auth regime
eliminates that requirement entirely.

## Design

### Deployment

Replace `iam-svc` with `no-auth-svc` in the processor group or
container configuration.  No other services change.  The no-auth
service listens on the standard IAM Pulsar topics:

- Request: `request:<topicspace>:iam`
- Response: `response:<topicspace>:iam`

### Dependencies

None.  No database, no config entries, no signing keys, no
bootstrap sequence.

### Operation responses

The service implements the IAM contract
([iam-contract.md](iam-contract.md)) with the following
behaviour for each operation:

| Operation | Behaviour |
|---|---|
| `authenticate-anonymous` | Returns a default identity: `user_id="anonymous"`, `workspace="default"`, `roles=["admin"]`.  This is the key operation that distinguishes no-auth from the full regime. |
| `resolve-api-key` | Accepts any token.  Returns the same default identity as `authenticate-anonymous`. |
| `authorise` | Always allows.  Returns `decision_allow=True`, `decision_ttl_seconds=3600`. |
| `authorise-many` | Always allows all checks. |
| `get-signing-key-public` | Returns an empty string.  The gateway skips JWT validation when no key is available. |
| `bootstrap` | No-op.  Returns empty admin user/key. |
| `bootstrap-status` | Returns `bootstrap_available=False`. |
| `whoami` | Returns a stub user record for the actor. |
| `login` | Returns empty JWT (not supported under no-auth). |
| `create-user`, `list-users`, `get-user`, `update-user`, `delete-user`, `disable-user`, `enable-user` | Return empty/stub responses.  User management is meaningless without auth. |
| `create-workspace`, `list-workspaces`, `get-workspace`, `update-workspace`, `disable-workspace` | Return empty/stub responses. |
| `create-api-key`, `list-api-keys`, `revoke-api-key` | Return empty/stub responses. |
| `change-password`, `reset-password` | No-op. |
| `rotate-signing-key` | No-op. |
| Unknown operation | Returns an error response (same as `iam-svc`). |

### Workspace resolution

When `resolve-api-key` is called, the returned workspace
determines which workspace the request operates against.  The
no-auth service defaults to `"default"`.

A configurable `--default-workspace` flag allows operators to
change this without code changes.

### Anonymous authentication

A new `authenticate-anonymous` operation is added to the IAM
protocol.  This is a small, backward-compatible addition to the
contract:

**Gateway change** (`auth.py`): when `authenticate()` receives a
request with no `Authorization` header (or an empty bearer
token), instead of immediately returning 401, it sends an
`authenticate-anonymous` request to the IAM service.  If the
regime returns a valid identity, the request proceeds.  If the
regime returns an error, the gateway returns 401 as before.

**`iam-svc` (full regime)**: returns `auth-failed` for
`authenticate-anonymous`.  Behaviour is unchanged — unauthenticated
requests are rejected exactly as they are today.

**`no-auth-svc`**: returns the default identity (`anonymous` /
`default` workspace).  No token required.

This keeps the policy decision ("is anonymous access allowed?")
in the IAM regime, not in the gateway.  The gateway is a generic
enforcement point that asks and respects the answer.

**Wire format**: uses the existing `IamRequest` / `IamResponse`
schema with `operation="authenticate-anonymous"`.  No new fields
required — the response uses `resolved_user_id`,
`resolved_workspace`, and `resolved_roles`, same as
`resolve-api-key`.

Requests that do carry a bearer token follow the existing
`resolve-api-key` / JWT paths unchanged.

## Implementation

### Service structure

The service is a standard `AsyncProcessor` that consumes IAM
requests and produces IAM responses, identical in shape to the
existing `iam-svc` processor:

```
trustgraph-flow/
  trustgraph/
    iam/
      noauth/
        __init__.py
        __main__.py
        service.py     # AsyncProcessor wiring
        handler.py     # Operation dispatch, always-allow logic
```

### Handler

The handler is a single `handle(request) -> response` function
with a dispatch table.  Each operation returns a pre-built
`IamResponse` with the appropriate fields set.  No database
access, no crypto, no state.

### Configuration

| Flag | Default | Description |
|---|---|---|
| `--default-workspace` | `"default"` | Workspace returned by `resolve-api-key` |
| `--default-user-id` | `"anonymous"` | User ID returned by `resolve-api-key` |

### Entry point

```
tg-no-auth-svc
```

Or via processor group:

```yaml
- class: trustgraph.iam.noauth.Processor
  params:
    <<: *defaults
    id: no-auth-svc
```

## Security considerations

This regime provides **no security whatsoever**.  Any caller with
network access to the API gateway has full admin access to all
workspaces.

Operators must ensure that network-level controls (firewall,
VPN, private network) provide adequate protection when deploying
this regime.  The regime is explicitly not suitable for multi-
tenant or internet-facing deployments.

## Testing

- Unit: verify each operation returns the expected stub response.
- Integration: deploy `no-auth-svc` in place of `iam-svc`, confirm
  the gateway starts, accepts requests with a dummy bearer token,
  and routes them to the default workspace.
- E2E: run the standard e2e test suite with `no-auth-svc` to
  confirm no regressions.
