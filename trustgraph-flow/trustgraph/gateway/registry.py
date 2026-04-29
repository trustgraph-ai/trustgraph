"""
Gateway operation registry.

Single declarative table mapping each operation the gateway
recognises to:

- The capability the IAM regime is asked to authorise against.
- The resource level (system / workspace / flow) — determines the
  shape of the resource identifier handed to ``authorise``.
- Extractors that build the resource and parameters from the
  request context.

This is a gateway-internal concept.  It is not part of the IAM
contract — the contract specifies what arguments ``authorise``
receives; the registry is how the gateway populates them.

See docs/tech-specs/iam-contract.md for the contract and
docs/tech-specs/iam.md for the request anatomy.
"""

from dataclasses import dataclass, field
from typing import Any, Callable


# Sentinels for operations that don't go through capability-based
# authorisation.  Mirror the values used in capabilities.py so the
# gateway endpoint layer can recognise them uniformly.
PUBLIC = "__public__"
AUTHENTICATED = "__authenticated__"


class ResourceLevel:
    """Where the operation's resource lives.

    ``SYSTEM``    — operation acts on a deployment-level resource
                    (the user registry, the workspace registry,
                    the signing key).  resource = {}.  Workspace,
                    if relevant, is a parameter, not an address.

    ``WORKSPACE`` — operation acts on something within a workspace
                    (config, library, knowledge, collections, flow
                    lifecycle).  resource = {workspace}.

    ``FLOW``      — operation acts on something within a flow
                    within a workspace (graph, agent, llm, etc.).
                    resource = {workspace, flow}.
    """
    SYSTEM = "system"
    WORKSPACE = "workspace"
    FLOW = "flow"


@dataclass
class RequestContext:
    """The bundle of inputs the registry's extractors operate on.
    Assembled by the gateway from the incoming request after
    authentication."""

    # Parsed JSON body (HTTP) or inner request payload (WebSocket).
    body: dict = field(default_factory=dict)

    # URL path components (HTTP) or WebSocket envelope routing
    # fields (id, service, workspace, flow).
    match_info: dict = field(default_factory=dict)

    # Authenticated identity for default-fill-in.  Always present
    # by the time extractors run, except for PUBLIC operations
    # where it is None.
    identity: Any = None


@dataclass
class Operation:
    """Declared operation the gateway can dispatch + authorise."""

    # Canonical operation name (used for registry lookup, audit,
    # debug logs).  Mirrors the operation strings in the IAM
    # service and other backends where applicable.
    name: str

    # Capability required to invoke this operation.  Either a
    # string from the capability vocabulary in capabilities.md, or
    # the PUBLIC / AUTHENTICATED sentinel for operations that
    # don't go through capability-based authorisation.
    capability: str

    # Where the operation's resource lives.  Determines the
    # shape of the resource argument passed to authorise.
    resource_level: str

    # Build the resource identifier from the request context.
    # Returns a dict with the appropriate components for the
    # resource level: {} for SYSTEM, {workspace} for WORKSPACE,
    # {workspace, flow} for FLOW.  Default-fill-in of workspace
    # from identity.workspace happens here when applicable.
    extract_resource: Callable[[RequestContext], dict]

    # Build the parameters dict — decision-relevant fields the
    # operation supplied that are not part of the resource
    # address.  E.g. workspace association on a system-level
    # user-registry operation.
    extract_parameters: Callable[[RequestContext], dict]


# ---------------------------------------------------------------------------
# Registry storage.
# ---------------------------------------------------------------------------


_REGISTRY: dict[str, Operation] = {}


def register(op: Operation) -> None:
    if op.name in _REGISTRY:
        raise RuntimeError(
            f"operation {op.name!r} already registered"
        )
    _REGISTRY[op.name] = op


def lookup(name: str) -> Operation | None:
    return _REGISTRY.get(name)


def all_operations() -> list[Operation]:
    return list(_REGISTRY.values())


# ---------------------------------------------------------------------------
# Common extractor helpers.
# ---------------------------------------------------------------------------


def _empty_resource(_ctx: RequestContext) -> dict:
    """System-level resource: empty dict."""
    return {}


def _workspace_from_body(ctx: RequestContext) -> dict:
    """Workspace-level resource sourced from the request body's
    workspace field, defaulting to the caller's bound workspace."""
    ws = (ctx.body.get("workspace") if isinstance(ctx.body, dict) else "")
    if not ws and ctx.identity is not None:
        ws = ctx.identity.workspace
    return {"workspace": ws}


def _flow_from_match_info(ctx: RequestContext) -> dict:
    """Flow-level resource sourced from URL path components or WS
    envelope fields.  Both ``workspace`` and ``flow`` are required;
    no default-fill-in (the address is the operation's identity)."""
    return {
        "workspace": ctx.match_info.get("workspace", ""),
        "flow": ctx.match_info.get("flow", ""),
    }


def _no_parameters(_ctx: RequestContext) -> dict:
    return {}


def _body_as_parameters(ctx: RequestContext) -> dict:
    """All body fields are parameters — used when the operation's
    body is small and uniformly decision-relevant (e.g. user-
    registry ops where the body's user.workspace is what the
    regime checks against the admin's scope)."""
    return dict(ctx.body) if isinstance(ctx.body, dict) else {}


def _workspace_param_only(ctx: RequestContext) -> dict:
    """Parameters dict carrying only the workspace association.
    Used by system-level operations (e.g. user-registry ops) where
    the workspace isn't part of the resource address but is the
    field the regime uses to scope the admin's authority.

    Pulls the workspace from the inner ``user`` / ``workspace_record``
    body field if present (create-user, create-workspace), then from
    the top-level body, then from the caller's bound workspace."""
    body = ctx.body if isinstance(ctx.body, dict) else {}
    inner_user = body.get("user") if isinstance(body.get("user"), dict) else {}
    inner_ws = (
        body.get("workspace_record")
        if isinstance(body.get("workspace_record"), dict) else {}
    )
    ws = (
        inner_user.get("workspace")
        or inner_ws.get("id")
        or body.get("workspace")
    )
    if not ws and ctx.identity is not None:
        ws = ctx.identity.workspace
    return {"workspace": ws or ""}


# ---------------------------------------------------------------------------
# Operation registrations.
#
# The gateway looks operations up by their canonical name (the same
# string the request body / WS envelope carries in its ``operation``
# field where applicable).  Auth-surface operations (login, bootstrap,
# change-password) are not listed here — they have their own routes
# in auth_endpoints.py and use PUBLIC / AUTHENTICATED sentinels
# directly.  Pure gateway↔IAM internal operations (resolve-api-key,
# authorise, authorise-many, get-signing-key-public) are likewise
# excluded; they are never invoked over the public API.
# ---------------------------------------------------------------------------


# IAM management operations.  All routed through /api/v1/iam, body
# carries ``operation`` plus operation-specific fields.

# User registry: SYSTEM-level resource (users are global, identified
# by handle).  The admin's authority is scoped per workspace via the
# parameters {workspace} field — that's what the regime checks
# against the admin's role workspace_scope.
register(Operation(
    name="create-user",
    capability="users:admin",
    resource_level=ResourceLevel.SYSTEM,
    extract_resource=_empty_resource,
    extract_parameters=_workspace_param_only,
))
register(Operation(
    name="list-users",
    capability="users:read",
    resource_level=ResourceLevel.SYSTEM,
    extract_resource=_empty_resource,
    extract_parameters=_workspace_param_only,
))
register(Operation(
    name="get-user",
    capability="users:read",
    resource_level=ResourceLevel.SYSTEM,
    extract_resource=_empty_resource,
    extract_parameters=_workspace_param_only,
))
register(Operation(
    name="update-user",
    capability="users:write",
    resource_level=ResourceLevel.SYSTEM,
    extract_resource=_empty_resource,
    extract_parameters=_workspace_param_only,
))
register(Operation(
    name="disable-user",
    capability="users:admin",
    resource_level=ResourceLevel.SYSTEM,
    extract_resource=_empty_resource,
    extract_parameters=_workspace_param_only,
))
register(Operation(
    name="enable-user",
    capability="users:admin",
    resource_level=ResourceLevel.SYSTEM,
    extract_resource=_empty_resource,
    extract_parameters=_workspace_param_only,
))
register(Operation(
    name="delete-user",
    capability="users:admin",
    resource_level=ResourceLevel.SYSTEM,
    extract_resource=_empty_resource,
    extract_parameters=_workspace_param_only,
))
register(Operation(
    name="reset-password",
    capability="users:admin",
    resource_level=ResourceLevel.SYSTEM,
    extract_resource=_empty_resource,
    extract_parameters=_workspace_param_only,
))


# API keys: SYSTEM-level resource — like users, a key record exists
# in the deployment-wide keys registry.  The workspace the key
# authenticates to is a property of the record, not a containment;
# it appears as a parameter so the regime can scope the admin's
# authority to issue / list / revoke against it.
register(Operation(
    name="create-api-key",
    capability="keys:admin",
    resource_level=ResourceLevel.SYSTEM,
    extract_resource=_empty_resource,
    extract_parameters=_workspace_param_only,
))
register(Operation(
    name="list-api-keys",
    capability="keys:admin",
    resource_level=ResourceLevel.SYSTEM,
    extract_resource=_empty_resource,
    extract_parameters=_workspace_param_only,
))
register(Operation(
    name="revoke-api-key",
    capability="keys:admin",
    resource_level=ResourceLevel.SYSTEM,
    extract_resource=_empty_resource,
    extract_parameters=_workspace_param_only,
))


# Workspace registry: SYSTEM-level resource (workspaces are the
# top-level addressable unit).  No parameters — the workspace being
# acted on is identified by the body, not used as a scope cue.
register(Operation(
    name="create-workspace",
    capability="workspaces:admin",
    resource_level=ResourceLevel.SYSTEM,
    extract_resource=_empty_resource,
    extract_parameters=_no_parameters,
))
register(Operation(
    name="list-workspaces",
    capability="workspaces:admin",
    resource_level=ResourceLevel.SYSTEM,
    extract_resource=_empty_resource,
    extract_parameters=_no_parameters,
))
register(Operation(
    name="get-workspace",
    capability="workspaces:admin",
    resource_level=ResourceLevel.SYSTEM,
    extract_resource=_empty_resource,
    extract_parameters=_no_parameters,
))
register(Operation(
    name="update-workspace",
    capability="workspaces:admin",
    resource_level=ResourceLevel.SYSTEM,
    extract_resource=_empty_resource,
    extract_parameters=_no_parameters,
))
register(Operation(
    name="disable-workspace",
    capability="workspaces:admin",
    resource_level=ResourceLevel.SYSTEM,
    extract_resource=_empty_resource,
    extract_parameters=_no_parameters,
))


# Signing key: SYSTEM-level operational op.
register(Operation(
    name="rotate-signing-key",
    capability="iam:admin",
    resource_level=ResourceLevel.SYSTEM,
    extract_resource=_empty_resource,
    extract_parameters=_no_parameters,
))


# ---------------------------------------------------------------------------
# Auth-surface entries.
#
# Listed here so the registry is the one place the gateway looks for
# operation→capability mappings — including the sentinels for paths
# that don't go through capability-based authorisation.  The actual
# routing is in auth_endpoints.py; these entries let the registry-
# driven dispatcher recognise the operation if it sees it on a
# generic path.
# ---------------------------------------------------------------------------

register(Operation(
    name="login",
    capability=PUBLIC,
    resource_level=ResourceLevel.SYSTEM,
    extract_resource=_empty_resource,
    extract_parameters=_no_parameters,
))
register(Operation(
    name="bootstrap",
    capability=PUBLIC,
    resource_level=ResourceLevel.SYSTEM,
    extract_resource=_empty_resource,
    extract_parameters=_no_parameters,
))
register(Operation(
    name="bootstrap-status",
    capability=PUBLIC,
    resource_level=ResourceLevel.SYSTEM,
    extract_resource=_empty_resource,
    extract_parameters=_no_parameters,
))
register(Operation(
    name="change-password",
    capability=AUTHENTICATED,
    resource_level=ResourceLevel.SYSTEM,
    extract_resource=_empty_resource,
    extract_parameters=_no_parameters,
))
register(Operation(
    name="whoami",
    capability=AUTHENTICATED,
    resource_level=ResourceLevel.SYSTEM,
    extract_resource=_empty_resource,
    extract_parameters=_no_parameters,
))


# ---------------------------------------------------------------------------
# Generic kind/operation entries.
#
# Names are ``<kind>:<operation>`` so the registry key is unique
# across dispatchers.  All entries below are workspace-level
# resources (workspace defaulted from the caller's bound workspace
# if absent).  Read/write distinction maps to the existing
# ``<subject>:read`` / ``<subject>:write`` capability vocabulary
# defined in capabilities.md.
# ---------------------------------------------------------------------------


def _register_kind_op(kind: str, op: str, capability: str) -> None:
    """Helper: register a workspace-level kind:op with the standard
    extractors (workspace from body, no extra parameters)."""
    register(Operation(
        name=f"{kind}:{op}",
        capability=capability,
        resource_level=ResourceLevel.WORKSPACE,
        extract_resource=_workspace_from_body,
        extract_parameters=_no_parameters,
    ))


# config: KV-style workspace config service.
for _op in ("get", "list", "getvalues", "getvalues-all-ws", "config"):
    _register_kind_op("config", _op, "config:read")
for _op in ("put", "delete"):
    _register_kind_op("config", _op, "config:write")


# flow: flow-blueprint and flow-lifecycle service.
for _op in ("list-blueprints", "get-blueprint", "list-flows", "get-flow"):
    _register_kind_op("flow", _op, "flows:read")
for _op in ("put-blueprint", "delete-blueprint", "start-flow", "stop-flow"):
    _register_kind_op("flow", _op, "flows:write")


# librarian: document storage and processing service.
for _op in (
    "get-document-metadata", "get-document-content",
    "stream-document", "list-documents", "list-processing",
    "get-upload-status", "list-uploads",
):
    _register_kind_op("librarian", _op, "documents:read")
for _op in (
    "add-document", "remove-document", "update-document",
    "add-processing", "remove-processing",
    "begin-upload", "upload-chunk", "complete-upload", "abort-upload",
):
    _register_kind_op("librarian", _op, "documents:write")


# knowledge: knowledge-graph core service.
for _op in ("get-kg-core", "list-kg-cores"):
    _register_kind_op("knowledge", _op, "knowledge:read")
for _op in ("put-kg-core", "delete-kg-core",
            "load-kg-core", "unload-kg-core"):
    _register_kind_op("knowledge", _op, "knowledge:write")


# collection-management: workspace collection lifecycle.
_register_kind_op("collection-management", "list-collections", "collections:read")
for _op in ("update-collection", "delete-collection"):
    _register_kind_op("collection-management", _op, "collections:write")


# ---------------------------------------------------------------------------
# Per-flow data-plane services.
#
# /api/v1/flow/{flow}/service/{kind} and the streaming
# /api/v1/flow/{flow}/{import,export}/{kind} paths.  No body-level
# ``operation`` discriminator — the URL kind is the operation
# identity.  Resource is FLOW level (workspace + flow).
#
# Names: ``flow-service:<kind>``, ``flow-import:<kind>``,
# ``flow-export:<kind>``.
# ---------------------------------------------------------------------------


def _register_flow_kind(prefix: str, kind: str, capability: str) -> None:
    register(Operation(
        name=f"{prefix}:{kind}",
        capability=capability,
        resource_level=ResourceLevel.FLOW,
        extract_resource=_flow_from_match_info,
        extract_parameters=_no_parameters,
    ))


# Request/response services on /api/v1/flow/{flow}/service/{kind}.
_FLOW_SERVICES = {
    "agent": "agent",
    "text-completion": "llm",
    "prompt": "llm",
    "mcp-tool": "mcp",
    "graph-rag": "graph:read",
    "document-rag": "documents:read",
    "embeddings": "embeddings",
    "graph-embeddings": "graph:read",
    "document-embeddings": "documents:read",
    "triples": "graph:read",
    "rows": "rows:read",
    "nlp-query": "rows:read",
    "structured-query": "rows:read",
    "structured-diag": "rows:read",
    "row-embeddings": "rows:read",
    "sparql": "graph:read",
}
for _kind, _cap in _FLOW_SERVICES.items():
    _register_flow_kind("flow-service", _kind, _cap)


# Streaming import socket endpoints.
_FLOW_IMPORTS = {
    "triples": "graph:write",
    "graph-embeddings": "graph:write",
    "document-embeddings": "documents:write",
    "entity-contexts": "documents:write",
    "rows": "rows:write",
}
for _kind, _cap in _FLOW_IMPORTS.items():
    _register_flow_kind("flow-import", _kind, _cap)


# Streaming export socket endpoints.
_FLOW_EXPORTS = {
    "triples": "graph:read",
    "graph-embeddings": "graph:read",
    "document-embeddings": "documents:read",
    "entity-contexts": "documents:read",
}
for _kind, _cap in _FLOW_EXPORTS.items():
    _register_flow_kind("flow-export", _kind, _cap)
