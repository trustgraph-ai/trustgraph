"""
Capability vocabulary, role definitions, and authorisation helpers.

See docs/tech-specs/capabilities.md for the authoritative description.
The data here is the OSS bundle table in that spec.  Enterprise
editions may replace this module with their own role table; the
vocabulary (capability strings) is shared.

Role model
----------
A role has two dimensions:

  1. **capability set** — which operations the role grants.
  2. **workspace scope** — which workspaces the role is active in.

The authorisation question is: *given the caller's roles, a required
capability, and a target workspace, does any role grant the
capability AND apply to the target workspace?*

Workspace scope values recognised here:

  - ``"assigned"`` — the role applies only to the caller's own
    assigned workspace (stored on their user record).
  - ``"*"`` — the role applies to every workspace.

Enterprise editions can add richer scopes (explicit permitted-set,
patterns, etc.) without changing the wire protocol.

Sentinels
---------
- ``PUBLIC`` — endpoint requires no authentication.
- ``AUTHENTICATED`` — endpoint requires a valid identity, no
  specific capability.
"""

from aiohttp import web


PUBLIC = "__public__"
AUTHENTICATED = "__authenticated__"


# Capability vocabulary.  Mirrors the "Capability list" tables in
# capabilities.md.  Kept as a set so the gateway can fail-closed on
# an endpoint that declares an unknown capability.
KNOWN_CAPABILITIES = {
    # Data plane
    "agent",
    "graph:read", "graph:write",
    "documents:read", "documents:write",
    "rows:read", "rows:write",
    "llm",
    "embeddings",
    "mcp",
    # Control plane
    "config:read", "config:write",
    "flows:read", "flows:write",
    "users:read", "users:write", "users:admin",
    "keys:self", "keys:admin",
    "workspaces:admin",
    "iam:admin",
    "metrics:read",
    "collections:read", "collections:write",
    "knowledge:read", "knowledge:write",
}


# Capability sets used below.
_READER_CAPS = {
    "agent",
    "graph:read",
    "documents:read",
    "rows:read",
    "llm",
    "embeddings",
    "mcp",
    "config:read",
    "flows:read",
    "collections:read",
    "knowledge:read",
    "keys:self",
}

_WRITER_CAPS = _READER_CAPS | {
    "graph:write",
    "documents:write",
    "rows:write",
    "collections:write",
    "knowledge:write",
}

_ADMIN_CAPS = _WRITER_CAPS | {
    "config:write",
    "flows:write",
    "users:read", "users:write", "users:admin",
    "keys:admin",
    "workspaces:admin",
    "iam:admin",
    "metrics:read",
}


# Role definitions.  Each role has a capability set and a workspace
# scope.  Enterprise overrides this mapping.
ROLE_DEFINITIONS = {
    "reader": {
        "capabilities": _READER_CAPS,
        "workspace_scope": "assigned",
    },
    "writer": {
        "capabilities": _WRITER_CAPS,
        "workspace_scope": "assigned",
    },
    "admin": {
        "capabilities": _ADMIN_CAPS,
        "workspace_scope": "*",
    },
}


def _scope_permits(role_name, target_workspace, assigned_workspace):
    """Does the given role apply to ``target_workspace``?"""
    role = ROLE_DEFINITIONS.get(role_name)
    if role is None:
        return False
    scope = role["workspace_scope"]
    if scope == "*":
        return True
    if scope == "assigned":
        return target_workspace == assigned_workspace
    # Future scope types (lists, patterns) extend here.
    return False


def check(identity, capability, target_workspace=None):
    """Is ``identity`` permitted to invoke ``capability`` on
    ``target_workspace``?

    Passes iff some role held by the caller both (a) grants
    ``capability`` and (b) is active in ``target_workspace``.

    ``target_workspace`` defaults to the caller's assigned workspace,
    which makes this function usable for system-level operations and
    for authenticated endpoints that don't take a workspace argument
    (the call collapses to "do any of my roles grant this cap?")."""
    if capability not in KNOWN_CAPABILITIES:
        return False

    target = target_workspace or identity.workspace

    for role_name in identity.roles:
        role = ROLE_DEFINITIONS.get(role_name)
        if role is None:
            continue
        if capability not in role["capabilities"]:
            continue
        if _scope_permits(role_name, target, identity.workspace):
            return True
    return False


def access_denied():
    return web.HTTPForbidden(
        text='{"error":"access denied"}',
        content_type="application/json",
    )


def auth_failure():
    return web.HTTPUnauthorized(
        text='{"error":"auth failure"}',
        content_type="application/json",
    )


async def enforce(request, auth, capability):
    """Authenticate + capability-check for endpoints that carry no
    workspace dimension on the request (metrics, i18n, etc.).

    For endpoints that carry a workspace field on the body, call
    :func:`enforce_workspace` *after* parsing the body to validate
    the workspace and re-check the capability in that scope.  Most
    endpoints do both.

    - ``PUBLIC``: no authentication, returns ``None``.
    - ``AUTHENTICATED``: any valid identity.
    - capability string: identity must have it, checked against the
      caller's assigned workspace (adequate for endpoints whose
      capability is system-level, e.g. ``metrics:read``, or where
      the real workspace-aware check happens in
      :func:`enforce_workspace` after body parsing)."""
    if capability == PUBLIC:
        return None

    identity = await auth.authenticate(request)

    if capability == AUTHENTICATED:
        return identity

    if not check(identity, capability):
        raise access_denied()

    return identity


def enforce_workspace(data, identity, capability=None):
    """Resolve + validate the workspace on a request body.

    - Target workspace = ``data["workspace"]`` if supplied, else the
      caller's assigned workspace.
    - At least one of the caller's roles must (a) be active in the
      target workspace and, if ``capability`` is given, (b) grant
      ``capability``.  Otherwise 403.
    - On success, ``data["workspace"]`` is overwritten with the
      resolved value — callers can rely on the outgoing message
      having the gateway's chosen workspace rather than any
      caller-supplied value.

    For ``capability=None`` the workspace scope alone is checked —
    useful when the body has a workspace but the endpoint already
    passed its capability check (e.g. via :func:`enforce`)."""
    if not isinstance(data, dict):
        return data

    requested = data.get("workspace", "")
    target = requested or identity.workspace

    for role_name in identity.roles:
        role = ROLE_DEFINITIONS.get(role_name)
        if role is None:
            continue
        if capability is not None and capability not in role["capabilities"]:
            continue
        if _scope_permits(role_name, target, identity.workspace):
            data["workspace"] = target
            return data

    raise access_denied()
