---
layout: default
title: "IAM Service Protocol Technical Specification"
parent: "Tech Specs"
---

# IAM Service Protocol Technical Specification

## Overview

The IAM service is a backend processor, reached over the standard
request/response pub/sub pattern. It is the authority for users,
workspaces, API keys, and login credentials. The API gateway
delegates to it for authentication resolution and for all user /
workspace / key management.

This document defines the wire protocol: the `IamRequest` and
`IamResponse` dataclasses, the operation set, the per-operation
input and output fields, the error taxonomy, and the initial HTTP
forwarding endpoint used while IAM is being integrated into the
gateway.

Architectural context — roles, capabilities, workspace scoping,
enforcement boundary — lives in [`iam.md`](iam.md) and
[`capabilities.md`](capabilities.md).

## Transport

- **Request topic:** `request:tg/request/iam-request`
- **Response topic:** `response:tg/response/iam-response`
- **Pattern:** request/response, correlated by the `id` message
  property, the same pattern used by `config-svc` and `flow-svc`.
- **Caller:** the API gateway only. Under the enforcement-boundary
  policy (see capabilities spec), the IAM service trusts the bus
  and performs no per-request authentication or capability check
  against the caller. The gateway has already evaluated capability
  membership and workspace scoping before sending the request.

## Dataclasses

### `IamRequest`

```python
@dataclass
class IamRequest:
    # One of the operation strings below.
    operation: str = ""

    # Scope of this request.  Required on every workspace-scoped
    # operation.  Omitted (or empty) for system-level ops
    # (workspace CRUD, signing-key ops, bootstrap, resolve-api-key,
    # login).
    workspace: str = ""

    # Acting user id, for audit.  Set by the gateway to the
    # authenticated caller's id on user-initiated operations.
    # Empty for internal-origin (bootstrap, reconcilers) and for
    # resolve-api-key / login (no actor yet).
    actor: str = ""

    # --- identity selectors ---
    user_id: str = ""
    username: str = ""          # login; unique within a workspace
    key_id: str = ""            # revoke-api-key, list-api-keys (own)
    api_key: str = ""           # resolve-api-key (plaintext)

    # --- credentials ---
    password: str = ""          # login, change-password (current)
    new_password: str = ""      # change-password

    # --- user fields ---
    user: UserInput | None = None       # create-user, update-user

    # --- workspace fields ---
    workspace_record: WorkspaceInput | None = None   # create-workspace, update-workspace

    # --- api key fields ---
    key: ApiKeyInput | None = None      # create-api-key
```

### `IamResponse`

```python
@dataclass
class IamResponse:
    # Populated on success of operations that return them.
    user: UserRecord | None = None              # create-user, get-user, update-user
    users: list[UserRecord] = field(default_factory=list)   # list-users
    workspace: WorkspaceRecord | None = None    # create-workspace, get-workspace, update-workspace
    workspaces: list[WorkspaceRecord] = field(default_factory=list)  # list-workspaces

    # create-api-key returns the plaintext once.  Never populated
    # on any other operation.
    api_key_plaintext: str = ""
    api_key: ApiKeyRecord | None = None          # create-api-key
    api_keys: list[ApiKeyRecord] = field(default_factory=list)  # list-api-keys

    # login, rotate-signing-key
    jwt: str = ""
    jwt_expires: str = ""        # ISO-8601 UTC

    # get-signing-key-public
    signing_key_public: str = ""  # PEM

    # resolve-api-key returns who this key authenticates as.
    resolved_user_id: str = ""
    resolved_workspace: str = ""
    resolved_roles: list[str] = field(default_factory=list)

    # reset-password
    temporary_password: str = ""  # returned once to the operator

    # bootstrap: on first run, the initial admin's one-time API key
    # is returned for the operator to capture.
    bootstrap_admin_user_id: str = ""
    bootstrap_admin_api_key: str = ""

    # Present on any failed operation.
    error: Error | None = None
```

### Value types

```python
@dataclass
class UserInput:
    username: str = ""
    name: str = ""
    email: str = ""
    password: str = ""          # only on create-user; never on update-user
    roles: list[str] = field(default_factory=list)
    enabled: bool = True
    must_change_password: bool = False

@dataclass
class UserRecord:
    id: str = ""
    workspace: str = ""
    username: str = ""
    name: str = ""
    email: str = ""
    roles: list[str] = field(default_factory=list)
    enabled: bool = True
    must_change_password: bool = False
    created: str = ""           # ISO-8601 UTC
    # Password hash is never included in any response.

@dataclass
class WorkspaceInput:
    id: str = ""
    name: str = ""
    enabled: bool = True

@dataclass
class WorkspaceRecord:
    id: str = ""
    name: str = ""
    enabled: bool = True
    created: str = ""           # ISO-8601 UTC

@dataclass
class ApiKeyInput:
    user_id: str = ""
    name: str = ""              # operator-facing label, e.g. "laptop"
    expires: str = ""           # optional ISO-8601 UTC; empty = no expiry

@dataclass
class ApiKeyRecord:
    id: str = ""
    user_id: str = ""
    name: str = ""
    prefix: str = ""            # first 4 chars of plaintext, for identification in lists
    expires: str = ""           # empty = no expiry
    created: str = ""
    last_used: str = ""         # empty if never used
    # key_hash is never included in any response.
```

## Operations

| Operation | Request fields | Response fields | Notes |
|---|---|---|---|
| `login` | `username`, `password`, `workspace` (optional) | `jwt`, `jwt_expires` | If `workspace` omitted, IAM resolves to the user's assigned workspace. |
| `resolve-api-key` | `api_key` (plaintext) | `resolved_user_id`, `resolved_workspace`, `resolved_roles` | Gateway-internal. Service returns `auth-failed` for unknown / expired / revoked keys. |
| `change-password` | `user_id`, `password` (current), `new_password` | — | Self-service. IAM validates `password` against stored hash. |
| `reset-password` | `user_id` | `temporary_password` | Admin-initiated. IAM generates a random password, sets `must_change_password=true` on the user, returns the plaintext once. |
| `create-user` | `workspace`, `user` | `user` | Admin-only. `user.password` is hashed and stored; `user.roles` must be subset of known roles. |
| `list-users` | `workspace` | `users` | |
| `get-user` | `workspace`, `user_id` | `user` | |
| `update-user` | `workspace`, `user_id`, `user` | `user` | `password` field on `user` is rejected; use `change-password` / `reset-password`. |
| `disable-user` | `workspace`, `user_id` | — | Soft-delete; sets `enabled=false`. Revokes all the user's API keys. |
| `create-workspace` | `workspace_record` | `workspace` | System-level. |
| `list-workspaces` | — | `workspaces` | System-level. |
| `get-workspace` | `workspace_record` (id only) | `workspace` | System-level. |
| `update-workspace` | `workspace_record` | `workspace` | System-level. |
| `disable-workspace` | `workspace_record` (id only) | — | System-level. Sets `enabled=false`; revokes all workspace API keys; disables all users in the workspace. |
| `create-api-key` | `workspace`, `key` | `api_key_plaintext`, `api_key` | Plaintext returned **once**; only hash stored. `key.name` required. |
| `list-api-keys` | `workspace`, `user_id` | `api_keys` | |
| `revoke-api-key` | `workspace`, `key_id` | — | Deletes the key record. |
| `get-signing-key-public` | — | `signing_key_public` | Gateway fetches this at startup. |
| `rotate-signing-key` | — | — | System-level. Introduces a new signing key; old key continues to validate JWTs for a grace period (implementation-defined, minimum 1h). |
| `bootstrap` | — | `bootstrap_admin_user_id`, `bootstrap_admin_api_key` | If IAM tables are empty, creates the initial `default` workspace, an `admin` user, an initial API key, and an initial signing key; returns them once. No-op on subsequent calls (returns empty fields). |

## Error taxonomy

All errors are carried in the `IamResponse.error` field. `error.type`
is one of the values below; `error.message` is a human-readable
string that is **not** surfaced verbatim to external callers (the
gateway maps to `auth failure` / `access denied` per the IAM error
policy).

| `type` | When |
|---|---|
| `invalid-argument` | Malformed request (missing required field, unknown operation, invalid format). |
| `not-found` | Named resource does not exist (`user_id`, `key_id`, workspace). |
| `duplicate` | Create operation collides with an existing resource (username, workspace id, key name). |
| `auth-failed` | `login` with wrong credentials; `resolve-api-key` with unknown / expired / revoked key; `change-password` with wrong current password. Single bucket to deny oracle attacks. |
| `weak-password` | Password does not meet policy (length, complexity — policy defined at service level). |
| `disabled` | Target user or workspace has `enabled=false`. |
| `operation-not-permitted` | Non-admin attempting system-level operation, or workspace-scoped operation attempting to affect another workspace. |
| `internal-error` | Unexpected IAM-side failure. Log and surface as 500 at the gateway. |

The gateway is responsible for translating `auth-failed` and
`operation-not-permitted` into the obfuscated external error
response (`"auth failure"` / `"access denied"`); `invalid-argument`
becomes a descriptive 400; `not-found` / `duplicate` /
`weak-password` / `disabled` become descriptive 4xx but never leak
IAM-internal detail.

## Credential storage

- **Passwords** are stored using a slow KDF (bcrypt / argon2id — the
  service picks; documented as an implementation detail). The
  `password_hash` column stores the full KDF-encoded string
  (algorithm, cost, salt, hash). Not a plain SHA-256.
- **API keys** are stored as SHA-256 of the plaintext. API keys
  are 128-bit random values (`tg_` + base64url); the entropy
  makes a slow hash unnecessary. The hash serves as the primary
  key on the `iam_api_keys` table, enabling O(1) lookup on
  `resolve-api-key`.
- **JWT signing key** is stored as an RSA or Ed25519 private key
  (implementation choice) in a dedicated `iam_signing_keys` table
  with a `kid`, `created`, and optional `retired` timestamp. At
  most one active key; up to N retired keys are kept for a grace
  period to validate previously-issued JWTs.

Passwords, API-key plaintext, and signing-key private material are
never returned in any response other than the explicit one-time
responses above (`reset-password`, `create-api-key`, `bootstrap`).

## Bootstrap modes

`iam-svc` requires a bootstrap mode to be chosen at startup. There is
no default — an unset or invalid mode causes the service to refuse
to start. The purpose is to force the operator to make an explicit
security decision rather than rely on an implicit "safe" fallback.

| Mode | Startup behaviour | `bootstrap` operation | Suitability |
|---|---|---|---|
| `token` | On first start with empty tables, auto-seeds the `default` workspace, admin user, admin API key (using the operator-provided `--bootstrap-token`), and an initial signing key. No-op on subsequent starts. | Refused — returns `auth-failed` / `"auth failure"` regardless of caller. | Production, any public-exposure deployment. |
| `bootstrap` | No startup seeding. Tables remain empty until the `bootstrap` operation is invoked over the pub/sub bus (typically via `tg-bootstrap-iam`). | Live while tables are empty. Generates and returns the admin API key once. Refused (`auth-failed`) once tables are populated. | Dev / compose up / CI. **Not safe under public exposure** — any caller reaching the gateway's `/api/v1/iam` forwarder before the operator can cause a token to be issued to them. Operators choosing this mode accept that risk. |

### Error masking

In both modes, any refused invocation of the `bootstrap` operation
returns the same error (`auth-failed` / `"auth failure"`). A caller
cannot distinguish:

- "service is in token mode"
- "service is in bootstrap mode but already bootstrapped"
- "operation forbidden"

This matches the general IAM error-policy stance (see `iam.md`) and
prevents externally enumerating IAM's state.

### Bootstrap-token lifecycle

The bootstrap token — whether operator-supplied (`token` mode) or
service-generated (`bootstrap` mode) — is a one-time credential. It
is stored as admin's single API key, tagged `name="bootstrap"`. The
operator's first admin action after bootstrap should be:

1. Create a durable admin user and API key (or issue a durable API
   key to the bootstrap admin).
2. Revoke the bootstrap key via `revoke-api-key`.
3. Remove the bootstrap token from any deployment configuration.

The `name="bootstrap"` marker makes bootstrap keys easy to detect in
tooling (e.g. a `tg-list-api-keys` filter).

## HTTP forwarding (initial integration)

For the initial gateway integration — before the IAM service is
wired into the authentication middleware — the gateway exposes a
single forwarding endpoint:

```
POST /api/v1/iam
```

- Request body is a JSON encoding of `IamRequest`.
- Response body is a JSON encoding of `IamResponse`.
- The gateway's existing authentication (`GATEWAY_SECRET` bearer)
  gates access to this endpoint so the IAM protocol can be
  exercised end-to-end in tests without touching the live auth
  path.
- This endpoint is **not** the final shape. Once the middleware is
  in place, per-operation REST endpoints replace it (for example
  `POST /api/v1/auth/login`, `POST /api/v1/users`, `DELETE
  /api/v1/api-keys/{id}`), and this generic forwarder is removed.

The endpoint performs only message marshalling: it does not read
or rewrite fields in the request, and it applies no capability
check. All authorisation for user / workspace / key management
lands in the subsequent middleware work.

## Non-goals for this spec

- REST endpoint shape for the final gateway surface — covered in
  Phase 2 of the IAM implementation plan, not here.
- OIDC / SAML external IdP protocol — out of scope for open source.
- Key-signing algorithm choice, password KDF choice, JWT claim
  layout — implementation details captured in code + ADRs, not
  locked in the protocol spec.

## References

- [Identity and Access Management Specification](iam.md)
- [Capability Vocabulary Specification](capabilities.md)
