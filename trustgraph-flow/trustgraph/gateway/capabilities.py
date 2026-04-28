"""
Gateway-side authorisation entry points.

Under the IAM contract (see docs/tech-specs/iam-contract.md) the
gateway holds *no* policy state.  Roles, capability sets, and
workspace-scope rules all live in the IAM regime (iam-svc for OSS).
This module is the thin surface the gateway uses to ask the regime
for a decision:

- ``PUBLIC`` / ``AUTHENTICATED`` sentinels for endpoints that don't
  go through capability-based authorisation.
- :func:`enforce` — authenticate-only, then ask the regime.
- :func:`enforce_workspace` — default-fill the workspace from the
  caller's bound workspace and ask the regime, with the workspace
  treated as the resource address.

The capability strings themselves are an open vocabulary — see
docs/tech-specs/capabilities.md.  The gateway does not validate them
beyond passing them through; an unknown capability simply produces a
deny verdict from the regime.
"""

from aiohttp import web


PUBLIC = "__public__"
AUTHENTICATED = "__authenticated__"


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
    """Authenticate the caller and (for non-sentinel capabilities)
    ask the IAM regime whether they may invoke ``capability``.

    The resource is system-level (``{}``) and parameters are empty —
    use :func:`enforce_workspace` for workspace-scoped endpoints, or
    drive authorisation through the operation registry for richer
    cases.

    - ``PUBLIC``: returns ``None`` — no authentication.
    - ``AUTHENTICATED``: returns the ``Identity`` — no authorisation.
    - capability string: returns the ``Identity`` if the regime
      allows; raises ``HTTPForbidden`` otherwise.
    """
    if capability == PUBLIC:
        return None

    identity = await auth.authenticate(request)

    if capability == AUTHENTICATED:
        return identity

    await auth.authorise(identity, capability, {}, {})
    return identity


async def enforce_workspace(data, identity, auth, capability=None):
    """Default-fill the workspace on a request body and (optionally)
    authorise the caller for ``capability`` against that workspace.

    - Target workspace = ``data["workspace"]`` if supplied, else the
      caller's bound workspace.
    - On success, ``data["workspace"]`` is overwritten with the
      resolved value so downstream code sees a single canonical
      address.
    - When ``capability`` is given, the regime is asked whether the
      caller may invoke ``capability`` on ``{workspace: target}``.
      Raises ``HTTPForbidden`` on a deny.

    For ``capability=None`` no authorisation call is made — the
    caller has presumably already authorised via :func:`enforce`
    (handy for endpoints that authorise once then resolve workspace
    on the body before forwarding).
    """
    if not isinstance(data, dict):
        return data

    requested = data.get("workspace", "")
    target = requested or identity.workspace
    data["workspace"] = target

    if capability is not None:
        await auth.authorise(
            identity, capability, {"workspace": target}, {},
        )

    return data
