---
layout: default
title: "Identity and Access Management"
parent: "Tech Specs"
---

# Identity and Access Management

## Problem Statement

TrustGraph has no meaningful identity or access management. The system
relies on a single shared gateway token for authentication and an
honour-system `user` query parameter for data isolation. This creates
several problems:

- **No user identity.** There are no user accounts, no login, and no way
  to know who is making a request. The `user` field in message metadata
  is a caller-supplied string with no validation — any client can claim
  to be any user.

- **No access control.** A valid gateway token grants unrestricted access
  to every endpoint, every user's data, every collection, and every
  administrative operation. There is no way to limit what an
  authenticated caller can do.

- **No credential isolation.** All callers share one static token. There
  is no per-user credential, no token expiration, and no rotation
  mechanism. Revoking access means changing the shared token, which
  affects all callers.

- **Data isolation is unenforced.** Storage backends (Cassandra, Neo4j,
  Qdrant) filter queries by `user` and `collection`, but the gateway
  does not prevent a caller from specifying another user's identity.
  Cross-user data access is trivial.

- **No audit trail.** There is no logging of who accessed what. Without
  user identity, audit logging is impossible.

These gaps make the system unsuitable for multi-user deployments,
multi-tenant SaaS, or any environment where access needs to be
controlled or audited.

## Current State

### Authentication

The API gateway supports a single shared token configured via the
`GATEWAY_SECRET` environment variable or `--api-token` CLI argument. If
unset, authentication is disabled entirely. When enabled, every HTTP
endpoint requires an `Authorization: Bearer <token>` header. WebSocket
connections pass the token as a query parameter.

Implementation: `trustgraph-flow/trustgraph/gateway/auth.py`

```python
class Authenticator:
    def __init__(self, token=None, allow_all=False):
        self.token = token
        self.allow_all = allow_all

    def permitted(self, token, roles):
        if self.allow_all: return True
        if self.token != token: return False
        return True
```

The `roles` parameter is accepted but never evaluated. All authenticated
requests have identical privileges.

MCP tool configurations support an optional per-tool `auth-token` for
service-to-service authentication with remote MCP servers. These are
static, system-wide tokens — not per-user credentials. See
[mcp-tool-bearer-token.md](mcp-tool-bearer-token.md) for details.

### User identity

The `user` field is passed explicitly by the caller as a query parameter
(e.g. `?user=trustgraph`) or set by CLI tools. It flows through the
system in the core `Metadata` dataclass:

```python
@dataclass
class Metadata:
    id: str = ""
    root: str = ""
    user: str = ""
    collection: str = ""
```

There is no user registration, login, user database, or session
management.

### Data isolation

The `user` + `collection` pair is used at the storage layer to partition
data:

- **Cassandra**: queries filter by `user` and `collection` columns
- **Neo4j**: queries filter by `user` and `collection` properties
- **Qdrant**: vector search filters by `user` and `collection` metadata

| Layer | Isolation mechanism | Enforced by |
|-------|-------------------|-------------|
| Gateway | Single shared token | `Authenticator` class |
| Message metadata | `user` + `collection` fields | Caller (honour system) |
| Cassandra | Column filters on `user`, `collection` | Query layer |
| Neo4j | Property filters on `user`, `collection` | Query layer |
| Qdrant | Metadata filters on `user`, `collection` | Query layer |
| Pub/sub topics | Per-flow topic namespacing | Flow service |

The storage-layer isolation depends on all queries correctly filtering by
`user` and `collection`. There is no gateway-level enforcement preventing
a caller from querying another user's data by passing a different `user`
parameter.

### Configuration and secrets

| Setting | Source | Default | Purpose |
|---------|--------|---------|---------|
| `GATEWAY_SECRET` | Env var | Empty (auth disabled) | Gateway bearer token |
| `--api-token` | CLI arg | None | Gateway bearer token (overrides env) |
| `PULSAR_API_KEY` | Env var | None | Pub/sub broker auth |
| MCP `auth-token` | Config service | None | Per-tool MCP server auth |

No secrets are encrypted at rest. The gateway token and MCP tokens are
stored and transmitted in plaintext (aside from any transport-layer
encryption such as TLS).

### Capabilities that do not exist

- Per-user authentication (JWT, OAuth, SAML, API keys per user)
- User accounts or user management
- Role-based access control (RBAC)
- Attribute-based access control (ABAC)
- Per-user or per-workspace API keys
- Token expiration or rotation
- Session management
- Per-user rate limiting
- Audit logging of user actions
- Permission checks preventing cross-user data access
- Multi-workspace credential isolation

### Key files

| File | Purpose |
|------|---------|
| `trustgraph-flow/trustgraph/gateway/auth.py` | Authenticator class |
| `trustgraph-flow/trustgraph/gateway/service.py` | Gateway init, token config |
| `trustgraph-flow/trustgraph/gateway/endpoint/*.py` | Per-endpoint auth checks |
| `trustgraph-base/trustgraph/schema/core/metadata.py` | `Metadata` dataclass with `user` field |

## Technical Design

### Design principles

- **Auth at the edge.** The gateway is the single enforcement point.
  Internal services trust the gateway and do not re-authenticate.
  This avoids distributing credential validation across dozens of
  microservices.

- **Identity from credentials, not from callers.** The gateway derives
  user identity from authentication credentials. Callers can no longer
  self-declare their identity via query parameters.

- **Workspace isolation by default.** Every authenticated user belongs to
  a workspace. All data operations are scoped to that workspace.
  Cross-workspace access is not possible through the API.

- **Extensible API contract.** The API accepts an optional workspace
  parameter on every request. This allows the same protocol to support
  single-workspace deployments today and multi-workspace extensions in
  the future without breaking changes.

- **Simple roles, not fine-grained permissions.** A small number of
  predefined roles controls what operations a user can perform. This is
  sufficient for the current API surface and avoids the complexity of
  per-resource permission management.

### Authentication

The gateway supports two credential types. Both are carried as a Bearer
token in the `Authorization` header for HTTP requests. The gateway
distinguishes them by format.

For WebSocket connections, credentials are not passed in the URL or
headers. Instead, the client authenticates after connecting by sending
an auth message as the first frame:

```
Client: opens WebSocket to /api/v1/socket
Server: accepts connection (unauthenticated state)
Client: sends {"type": "auth", "token": "tg_abc123..."}
Server: validates token
  success → {"type": "auth-ok", "workspace": "acme"}
  failure → {"type": "auth-failed", "error": "invalid token"}
```

The server rejects all non-auth messages until authentication succeeds.
The socket remains open on auth failure, allowing the client to retry
with a different token without reconnecting. The client can also send
a new auth message at any time to re-authenticate — for example, to
refresh an expiring JWT or to switch workspace. The
resolved identity (user, workspace, roles) is updated on each
successful auth.

#### API keys

For programmatic access: CLI tools, scripts, and integrations.

- Opaque tokens (e.g. `tg_a1b2c3d4e5f6...`). Not JWTs — short,
  simple, easy to paste into CLI tools and headers.
- Each user has one or more API keys.
- Keys are stored hashed (SHA-256 with salt) in the IAM service. The
  plaintext key is returned once at creation time and cannot be
  retrieved afterwards.
- Keys can be revoked individually without affecting other users.
- Keys optionally have an expiry date. Expired keys are rejected.

On each request, the gateway resolves an API key by:

1. Hashing the token.
2. Checking a local cache (hash → user/workspace/roles).
3. On cache miss, calling the IAM service to resolve.
4. Caching the result with a short TTL (e.g. 60 seconds).

Revoked keys stop working when the cache entry expires. No push
invalidation is needed.

#### JWTs (login sessions)

For interactive access via the UI or WebSocket connections.

- A user logs in with username and password. The gateway forwards the
  request to the IAM service, which validates the credentials and
  returns a signed JWT.
- The JWT carries the user ID, workspace, and roles as claims.
- The gateway validates JWTs locally using the IAM service's public
  signing key — no service call needed on subsequent requests.
- Token expiry is enforced by standard JWT validation at the time the
  request (or WebSocket connection) is made.
- For long-lived WebSocket connections, the JWT is validated at connect
  time only. The connection remains authenticated for its lifetime.

The IAM service manages the signing key. The gateway fetches the public
key at startup (or on first JWT encounter) and caches it.

#### Login endpoint

```
POST /api/v1/auth/login
{
    "username": "alice",
    "password": "..."
}
→ {
    "token": "eyJ...",
    "expires": "2026-04-20T19:00:00Z"
}
```

The gateway forwards this to the IAM service, which validates
credentials and returns a signed JWT. The gateway returns the JWT to
the caller.

#### IAM service delegation

The gateway stays thin. Its authentication logic is:

1. Extract Bearer token from header (or query param for WebSocket).
2. If the token has JWT format (dotted structure), validate the
   signature locally and extract claims.
3. Otherwise, treat as an API key: hash it and check the local cache.
   On cache miss, call the IAM service to resolve.
4. If neither succeeds, return 401.

All user management, key management, credential validation, and token
signing logic lives in the IAM service. The gateway is a generic
enforcement point that can be replaced without changing the IAM
service.

#### No legacy token support

The existing `GATEWAY_SECRET` shared token is removed. All
authentication uses API keys or JWTs. On first start, the bootstrap
process creates a default workspace and admin user with an initial API
key.

### User identity

A user belongs to exactly one workspace. The design supports extending
this to multi-workspace access in the future (see
[Extension points](#extension-points)).

A user record contains:

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique user identifier (UUID) |
| `name` | string | Display name |
| `email` | string | Email address (optional) |
| `workspace` | string | Workspace the user belongs to |
| `roles` | list[string] | Assigned roles (e.g. `["reader"]`) |
| `enabled` | bool | Whether the user can authenticate |
| `created` | datetime | Account creation timestamp |

The `workspace` field maps to the existing `user` field in `Metadata`.
This means the storage-layer isolation (Cassandra, Neo4j, Qdrant
filtering by `user` + `collection`) works without changes — the gateway
sets the `user` metadata field to the authenticated user's workspace.

### Workspaces

A workspace is an isolated data boundary. Users belong to a workspace,
and all data operations are scoped to it. Workspaces map to the existing
`user` field in `Metadata` and the corresponding Cassandra keyspace,
Qdrant collection prefix, and Neo4j property filters.

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique workspace identifier |
| `name` | string | Display name |
| `enabled` | bool | Whether the workspace is active |
| `created` | datetime | Creation timestamp |

All data operations are scoped to a workspace. The gateway determines
the effective workspace for each request as follows:

1. If the request includes a `workspace` parameter, validate it against
   the user's assigned workspace.
   - If it matches, use it.
   - If it does not match, return 403. (This could be extended to
     check a workspace access grant list.)
2. If no `workspace` parameter is provided, use the user's assigned
   workspace.

The gateway sets the `user` field in `Metadata` to the effective
workspace ID, replacing the caller-supplied `?user=` query parameter.

This design ensures forward compatibility. Clients that pass a
workspace parameter will work unchanged if multi-workspace support is
added later. Requests for an unassigned workspace get a clear 403
rather than silent misbehaviour.

### Roles and access control

Three roles with fixed permissions:

| Role | Data operations | Admin operations | System |
|------|----------------|-----------------|--------|
| `reader` | Query knowledge graph, embeddings, RAG | None | None |
| `writer` | All reader operations + load documents, manage collections | None | None |
| `admin` | All writer operations | Config, flows, collection management, user management | Metrics |

Role checks happen at the gateway before dispatching to backend
services. Each endpoint declares the minimum role required:

| Endpoint pattern | Minimum role |
|-----------------|--------------|
| `GET /api/v1/socket` (queries) | `reader` |
| `POST /api/v1/librarian` | `writer` |
| `POST /api/v1/flow/*/import/*` | `writer` |
| `POST /api/v1/config` | `admin` |
| `GET /api/v1/flow/*` | `admin` |
| `GET /api/metrics` | `admin` |

Roles are hierarchical: `admin` implies `writer`, which implies
`reader`.

### IAM service

The IAM service is a new backend service that manages all identity and
access data. It is the authority for users, workspaces, API keys, and
credentials. The gateway delegates to it.

#### Data model

```
iam_workspaces (
    id text PRIMARY KEY,
    name text,
    enabled boolean,
    created timestamp
)

iam_users (
    id text PRIMARY KEY,
    workspace text,
    name text,
    email text,
    password_hash text,
    roles set<text>,
    enabled boolean,
    created timestamp
)

iam_api_keys (
    key_hash text PRIMARY KEY,
    user_id text,
    name text,
    expires timestamp,
    created timestamp
)
```

A secondary index on `iam_api_keys.user_id` supports listing a user's
keys.

#### Responsibilities

- User CRUD (create, list, update, disable)
- Workspace CRUD (create, list, update, disable)
- API key management (create, revoke, list)
- API key resolution (hash → user/workspace/roles)
- Credential validation (username/password → signed JWT)
- JWT signing key management (initialise, rotate)
- Bootstrap (create default workspace and admin user on first start)

#### Communication

The IAM service communicates via the standard request/response pub/sub
pattern, the same as the config service. The gateway calls it to
resolve API keys and to handle login requests. User management
operations (create user, revoke key, etc.) also go through the IAM
service.

### Error policy

External error responses carry **no diagnostic detail** for
authentication or access-control failures. The goal is to give an
attacker probing the endpoint no signal about which condition they
tripped.

| Category | HTTP | Body | WebSocket frame |
|----------|------|------|-----------------|
| Authentication failure | `401 Unauthorized` | `{"error": "auth failure"}` | `{"type": "auth-failed", "error": "auth failure"}` |
| Access control failure | `403 Forbidden` | `{"error": "access denied"}` | `{"error": "access denied"}` (endpoint-specific frame type) |

"Authentication failure" covers missing credential, malformed
credential, invalid signature, expired token, revoked API key, and
unknown API key — all indistinguishable to the caller.

"Access control failure" covers role insufficient, workspace
mismatch, user disabled, and workspace disabled — all
indistinguishable to the caller.

**Server-side logging is richer.** The audit log records the specific
reason (`"workspace-mismatch: user alice assigned 'acme', requested
'beta'"`, `"role-insufficient: admin required, user has writer"`,
etc.) for operators and post-incident forensics. These messages never
appear in responses.

Other error classes (bad request, internal error) remain descriptive
because they do not reveal anything about the auth or access-control
surface — e.g. `"missing required field 'workspace'"` or
`"invalid JSON"` is fine.

### Gateway changes

The current `Authenticator` class is replaced with a thin authentication
middleware that delegates to the IAM service:

For HTTP requests:

1. Extract Bearer token from the `Authorization` header.
2. If the token has JWT format (dotted structure):
   - Validate signature locally using the cached public key.
   - Extract user ID, workspace, and roles from claims.
3. Otherwise, treat as an API key:
   - Hash the token and check the local cache.
   - On cache miss, call the IAM service to resolve.
   - Cache the result (user/workspace/roles) with a short TTL.
4. If neither succeeds, return 401.
5. If the user or workspace is disabled, return 403.
6. Check the user's role against the endpoint's minimum role. If
   insufficient, return 403.
7. Resolve the effective workspace:
   - If the request includes a `workspace` parameter, validate it
     against the user's assigned workspace. Return 403 on mismatch.
   - If no `workspace` parameter, use the user's assigned workspace.
8. Set the `user` field in the request context to the effective
   workspace ID. This propagates through `Metadata` to all downstream
   services.

For WebSocket connections:

1. Accept the connection in an unauthenticated state.
2. Wait for an auth message (`{"type": "auth", "token": "..."}`).
3. Validate the token using the same logic as steps 2-7 above.
4. On success, attach the resolved identity to the connection and
   send `{"type": "auth-ok", ...}`.
5. On failure, send `{"type": "auth-failed", ...}` but keep the
   socket open.
6. Reject all non-auth messages until authentication succeeds.
7. Accept new auth messages at any time to re-authenticate.

### CLI changes

CLI tools authenticate with API keys:

- `--api-key` argument on all CLI tools, replacing `--api-token`.
- `tg-create-workspace`, `tg-list-workspaces` for workspace management.
- `tg-create-user`, `tg-list-users`, `tg-disable-user` for user
  management.
- `tg-create-api-key`, `tg-list-api-keys`, `tg-revoke-api-key` for
  key management.
- `--workspace` argument on tools that operate on workspace-scoped
  data.
- The API key is passed as a Bearer token in the same way as the
  current shared token, so the transport protocol is unchanged.

### Audit logging

With user identity established, the gateway logs:

- Timestamp, user ID, workspace, endpoint, HTTP method, response status.
- Audit logs are written to the standard logging output (structured
  JSON). Integration with external log aggregation (Loki, ELK) is a
  deployment concern, not an application concern.

### Config service changes

All configuration is workspace-scoped (see
[data-ownership-model.md](data-ownership-model.md)). The config service
needs to support this.

#### Schema change

The config table adds workspace as a key dimension:

```
config (
    workspace text,
    class text,
    key text,
    value text,
    PRIMARY KEY ((workspace, class), key)
)
```

#### Request format

Config requests add a `workspace` field at the request level. The
existing `(type, key)` structure is unchanged within each workspace.

**Get:**
```json
{
    "operation": "get",
    "workspace": "workspace-a",
    "keys": [{"type": "prompt", "key": "rag-prompt"}]
}
```

**Put:**
```json
{
    "operation": "put",
    "workspace": "workspace-a",
    "values": [{"type": "prompt", "key": "rag-prompt", "value": "..."}]
}
```

**List (all keys of a type within a workspace):**
```json
{
    "operation": "list",
    "workspace": "workspace-a",
    "type": "prompt"
}
```

**Delete:**
```json
{
    "operation": "delete",
    "workspace": "workspace-a",
    "keys": [{"type": "prompt", "key": "rag-prompt"}]
}
```

The workspace is set by:

- **Gateway** — from the authenticated user's workspace for API-facing
  requests.
- **Internal services** — explicitly, based on `Metadata.user` from
  the message being processed, or `_system` for operational config.

#### System config namespace

Processor-level operational config (logging levels, connection strings,
resource limits) is not workspace-specific. This stays in a reserved
`_system` workspace that is not associated with any user workspace.
Services read system config at startup without needing a workspace
context.

#### Config change notifications

The config notify mechanism pushes change notifications via pub/sub
when config is updated. A single update may affect multiple workspaces
and multiple config types. The notification message carries a dict of
changes keyed by config type, with each value being the list of
affected workspaces:

```json
{
    "version": 42,
    "changes": {
        "prompt": ["workspace-a", "workspace-b"],
        "schema": ["workspace-a"]
    }
}
```

System config changes use the reserved `_system` workspace:

```json
{
    "version": 43,
    "changes": {
        "logging": ["_system"]
    }
}
```

This structure is keyed by type because handlers register by type. A
handler registered for `prompt` looks up `"prompt"` directly and gets
the list of affected workspaces — no iteration over unrelated types.

#### Config change handlers

The current `on_config` hook mechanism needs two modes to support shared
processing services:

- **Workspace-scoped handlers** — notify when a config type changes in a
  specific workspace. The handler looks up its registered type in the
  changes dict and checks if its workspace is in the list. Used by the
  gateway and by services that serve a single workspace.

- **Global handlers** — notify when a config type changes in any
  workspace. The handler looks up its registered type in the changes
  dict and gets the full list of affected workspaces. Used by shared
  processing services (prompt-rag, agent manager, etc.) that serve all
  workspaces. Each workspace in the list tells the handler which cache
  entry to update rather than reloading everything.

#### Per-workspace config caching

Shared services that handle messages from multiple workspaces maintain a
per-workspace config cache. When a message arrives, the service looks up
the config for the workspace identified in `Metadata.user`. If the
workspace is not yet cached, the service fetches its config on demand.
Config change notifications update the relevant cache entry.

### Flow and queue isolation

Flows are workspace-owned. When two workspaces start flows with the same
name and blueprint, their queues must be separate to prevent data
mixing.

Flow blueprint templates currently use `{id}` (flow instance ID) and
`{class}` (blueprint name) as template variables in queue names. A new
`{workspace}` variable is added so queue names include the workspace:

**Current queue names (no workspace isolation):**
```
flow:tg:document-load:{id}         → flow:tg:document-load:default
request:tg:embeddings:{class}      → request:tg:embeddings:everything
```

**With workspace isolation:**
```
flow:tg:{workspace}:document-load:{id}      → flow:tg:ws-a:document-load:default
request:tg:{workspace}:embeddings:{class}   → request:tg:ws-a:embeddings:everything
```

The flow service substitutes `{workspace}` from the authenticated
workspace when starting a flow, the same way it substitutes `{id}` and
`{class}` today.

Processing services are shared infrastructure — they consume from
workspace-specific queues but are not themselves workspace-aware. The
workspace is carried in `Metadata.user` on every message, so services
know which workspace's data they are processing.

Blueprint templates need updating to include `{workspace}` in all queue
name patterns. For migration, the flow service can inject the workspace
into queue names automatically if the template does not include
`{workspace}`, defaulting to the legacy behaviour for existing
blueprints.

See [flow-class-definition.md](flow-class-definition.md) for the full
blueprint template specification.

### What changes and what doesn't

**Changes:**

| Component | Change |
|-----------|--------|
| `gateway/auth.py` | Replace `Authenticator` with new auth middleware |
| `gateway/service.py` | Initialise IAM client, configure JWT validation |
| `gateway/endpoint/*.py` | Add role requirement per endpoint |
| Metadata propagation | Gateway sets `user` from workspace, ignores query param |
| Config service | Add workspace dimension to config schema |
| Config table | `PRIMARY KEY ((workspace, class), key)` |
| Config request/response schema | Add `workspace` field |
| Config notify messages | Include workspace ID in change notifications |
| `on_config` handlers | Support workspace-scoped and global modes |
| Shared services | Per-workspace config caching |
| Flow blueprints | Add `{workspace}` template variable to queue names |
| Flow service | Substitute `{workspace}` when starting flows |
| CLI tools | New user management commands, `--api-key` argument |
| Cassandra schema | New `iam_workspaces`, `iam_users`, `iam_api_keys` tables |

**Does not change:**

| Component | Reason |
|-----------|--------|
| Internal service-to-service pub/sub | Services trust the gateway |
| `Metadata` dataclass | `user` field continues to carry workspace identity |
| Storage-layer isolation | Same `user` + `collection` filtering |
| Message serialisation | No schema changes |

### Migration

This is a breaking change. Existing deployments must be reconfigured:

1. `GATEWAY_SECRET` is removed. Authentication requires API keys or
   JWT login tokens.
2. The `?user=` query parameter is removed. Workspace identity comes
   from authentication.
3. On first start, the IAM service bootstraps a default workspace and
   admin user. The initial API key is output to the service log.
4. Operators create additional workspaces and users via CLI tools.
5. Flow blueprints must be updated to include `{workspace}` in queue
   name patterns.
6. Config data must be migrated to include the workspace dimension.

## Extension points

The design includes deliberate extension points for future capabilities.
These are not implemented but the architecture does not preclude them:

- **Multi-workspace access.** Users could be granted access to
  additional workspaces beyond their primary assignment. The workspace
  validation step checks a grant list instead of a single assignment.
- **Workspace resolver.** Workspace resolution on each authenticated
  request — "given this user and this requested workspace, which
  workspace (if any) may the request operate on?" — is encapsulated
  in a single pluggable resolver. The open-source edition ships a
  resolver that permits only the user's single assigned workspace;
  enterprise editions that implement multi-workspace access swap in a
  resolver that consults a permitted set. The wire protocol (the
  optional `workspace` field on the authenticated request) is
  identical in both editions, so clients written against one edition
  work unchanged against the other.
- **Rules-based access control.** A separate access control service
  could evaluate fine-grained policies (per-collection permissions,
  operation-level restrictions, time-based access). The gateway
  delegates authorisation decisions to this service.
- **External identity provider integration.** SAML, LDAP, and OIDC
  flows (group mapping, claims-based role assignment) could be added
  to the IAM service.
- **Cross-workspace administration.** A `superadmin` role for platform
  operators who manage multiple workspaces.
- **Delegated workspace provisioning.** APIs for programmatic workspace
  creation and user onboarding.

These extensions are additive — they extend the validation logic
without changing the request/response protocol. The gateway can be
replaced with an alternative implementation that supports these
capabilities while the IAM service and backend services remain
unchanged.

## Implementation plan

Workspace support is a prerequisite for auth — users are assigned to
workspaces, config is workspace-scoped, and flows use workspace in
queue names. Implementing workspaces first allows the structural changes
to be tested end-to-end without auth complicating debugging.

### Phase 1: Workspace support (no auth)

All workspace-scoped data and processing changes. The system works with
workspaces but no authentication — callers pass workspace as a
parameter, honour system. This allows full end-to-end testing: multiple
workspaces with separate flows, config, queues, and data.

#### Config service

- Update config client API to accept a workspace parameter on all
  requests
- Update config storage schema to add workspace as a key dimension
- Update config notification API to report changes as a dict of
  type → workspace list
- Update the processor base class to understand workspaces in config
  notifications (workspace-scoped and global handler modes)
- Update all processors to implement workspace-aware config handling
  (per-workspace config caching, on-demand fetch)

#### Flow and queue isolation

- Update flow blueprints to include `{workspace}` in all queue name
  patterns
- Update the flow service to substitute `{workspace}` when starting
  flows
- Update all built-in blueprints to include `{workspace}`

#### CLI tools (workspace support)

- Add `--workspace` argument to CLI tools that operate on
  workspace-scoped data
- Add `tg-create-workspace`, `tg-list-workspaces` commands

### Phase 2: Authentication and access control

With workspaces working, add the IAM service and lock down the gateway.

#### IAM service

A new service handling identity and access management on behalf of the
API gateway:

- Add workspace table support (CRUD, enable/disable)
- Add user table support (CRUD, enable/disable, workspace assignment)
- Add roles support (role assignment, role validation)
- Add API key support (create, revoke, list, hash storage)
- Add ability to initialise a JWT signing key for token grants
- Add token grant endpoint: user/password login returns a signed JWT
- Add bootstrap/initialisation mechanism: ability to set the signing
  key and create the initial workspace + admin user on first start

#### API gateway integration

- Add IAM middleware to the API gateway replacing the current
  `Authenticator`
- Add local JWT validation (public key from IAM service)
- Add API key resolution with local cache (hash → user/workspace/roles,
  cache miss calls IAM service, short TTL)
- Add login endpoint forwarding to IAM service
- Add workspace resolution: validate requested workspace against user
  assignment
- Add role-based endpoint access checks
- Add user management API endpoints (forwarded to IAM service)
- Add audit logging (user ID, workspace, endpoint, method, status)
- WebSocket auth via first-message protocol (auth message after
  connect, socket stays open on failure, re-auth supported)

#### CLI tools (auth support)

- Add `tg-create-user`, `tg-list-users`, `tg-disable-user` commands
- Add `tg-create-api-key`, `tg-list-api-keys`, `tg-revoke-api-key`
  commands
- Replace `--api-token` with `--api-key` on existing CLI tools

#### Bootstrap and cutover

- Create default workspace and admin user on first start if IAM tables
  are empty
- Remove `GATEWAY_SECRET` and `?user=` query parameter support

## Design Decisions

### IAM data store

IAM data is stored in dedicated Cassandra tables owned by the IAM
service, not in the config service. Reasons:

- **Security isolation.** The config service has a broad, generic
  protocol. An access control failure on the config service could
  expose credentials. A dedicated IAM service with a purpose-built
  protocol limits the attack surface and makes security auditing
  clearer.
- **Data model fit.** IAM needs indexed lookups (API key hash → user,
  list keys by user). The config service's `(workspace, type, key) →
  value` model stores opaque JSON strings with no secondary indexes.
- **Scope.** IAM data is global (workspaces, users, keys). Config is
  workspace-scoped. Mixing global and workspace-scoped data in the
  same store adds complexity.
- **Audit.** IAM operations (key creation, revocation, login attempts)
  are security events that should be logged separately from general
  config changes.

## Deferred to future design

- **OIDC integration.** External identity provider support (SAML, LDAP,
  OIDC) is left for future implementation. The extension points section
  describes where this fits architecturally.
- **API key scoping.** API keys could be scoped to specific collections
  within a workspace rather than granting workspace-wide access. To be
  designed when the need arises.

## References

- [Data Ownership and Information Separation](data-ownership-model.md)
- [MCP Tool Bearer Token Specification](mcp-tool-bearer-token.md)
- [Multi-Tenant Support Specification](multi-tenant-support.md)
- [Neo4j User Collection Isolation](neo4j-user-collection-isolation.md)
