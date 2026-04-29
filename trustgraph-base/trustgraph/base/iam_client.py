
import json

from . request_response_spec import RequestResponse, RequestResponseSpec
from .. schema import (
    IamRequest, IamResponse,
    UserInput, WorkspaceInput, ApiKeyInput,
)

IAM_TIMEOUT = 10


class IamClient(RequestResponse):
    """Client for the IAM service request/response pub/sub protocol.

    Mirrors ``ConfigClient``: a thin wrapper around ``RequestResponse``
    that knows the IAM request / response schemas.  Only the subset of
    operations actually implemented by the server today has helper
    methods here; callers that need an unimplemented operation can
    build ``IamRequest`` and call ``request()`` directly.
    """

    async def _request(self, timeout=IAM_TIMEOUT, **kwargs):
        resp = await self.request(
            IamRequest(**kwargs),
            timeout=timeout,
        )
        if resp.error:
            raise RuntimeError(
                f"{resp.error.type}: {resp.error.message}"
            )
        return resp

    async def bootstrap(self, timeout=IAM_TIMEOUT):
        """Initial-run IAM self-seed.  Returns a tuple of
        ``(admin_user_id, admin_api_key_plaintext)``.  Both are empty
        strings on repeat calls — the operation is a no-op once the
        IAM tables are populated."""
        resp = await self._request(
            operation="bootstrap", timeout=timeout,
        )
        return resp.bootstrap_admin_user_id, resp.bootstrap_admin_api_key

    async def bootstrap_status(self, timeout=IAM_TIMEOUT):
        """Returns whether an unconsumed ``bootstrap`` call would
        currently succeed (i.e. iam-svc is in ``bootstrap`` mode and
        its tables are empty).  Side-effect-free; intended for first-
        run UX so a UI can decide whether to render setup."""
        resp = await self._request(
            operation="bootstrap-status", timeout=timeout,
        )
        return resp.bootstrap_available

    async def whoami(self, actor, timeout=IAM_TIMEOUT):
        """Return the user record for ``actor`` (the authenticated
        caller's handle).  AUTHENTICATED-only; no capability check —
        every authenticated user can read themselves."""
        resp = await self._request(
            operation="whoami",
            actor=actor,
            timeout=timeout,
        )
        return resp.user

    async def resolve_api_key(self, api_key, timeout=IAM_TIMEOUT):
        """Resolve a plaintext API key to its identity triple.

        Returns ``(user_id, workspace, roles)`` or raises
        ``RuntimeError`` with error type ``auth-failed`` if the key is
        unknown / expired / revoked.

        Note: the ``roles`` value is a regime-internal hint and is
        not used by the gateway directly under the IAM contract;
        all authorisation decisions go through ``authorise()``.
        Returned here only for backward compatibility with callers
        that haven't migrated."""
        resp = await self._request(
            operation="resolve-api-key",
            api_key=api_key,
            timeout=timeout,
        )
        return (
            resp.resolved_user_id,
            resp.resolved_workspace,
            list(resp.resolved_roles),
        )

    async def authorise(self, identity_handle, capability,
                        resource, parameters, timeout=IAM_TIMEOUT):
        """Ask the IAM regime whether ``identity_handle`` may perform
        ``capability`` on ``resource`` given ``parameters``.

        Implements the contract ``authorise(identity, capability,
        resource, parameters) → (decision, ttl)``.  Returns a tuple
        ``(allow: bool, ttl_seconds: int)``.  The TTL is the
        regime's suggested cache lifetime for this decision; the
        gateway honours it (clamped above by gateway-side policy)."""
        resp = await self._request(
            operation="authorise",
            user_id=identity_handle,
            capability=capability,
            resource_json=json.dumps(resource or {}, sort_keys=True),
            parameters_json=json.dumps(parameters or {}, sort_keys=True),
            timeout=timeout,
        )
        return resp.decision_allow, resp.decision_ttl_seconds

    async def authorise_many(self, identity_handle, checks,
                             timeout=IAM_TIMEOUT):
        """Bulk authorise.  ``checks`` is a list of dicts each
        carrying ``capability``, ``resource``, and ``parameters``.
        Returns a list of ``(allow, ttl)`` tuples in the same order."""
        resp = await self._request(
            operation="authorise-many",
            user_id=identity_handle,
            authorise_checks=json.dumps(list(checks), sort_keys=True),
            timeout=timeout,
        )
        decisions = json.loads(resp.decisions_json or "[]")
        return [(d.get("allow", False), d.get("ttl", 0)) for d in decisions]

    async def create_user(self, workspace, user, actor="",
                          timeout=IAM_TIMEOUT):
        """Create a user.  ``user`` is a ``UserInput``."""
        resp = await self._request(
            operation="create-user",
            workspace=workspace,
            actor=actor,
            user=user,
            timeout=timeout,
        )
        return resp.user

    async def list_users(self, workspace, actor="", timeout=IAM_TIMEOUT):
        resp = await self._request(
            operation="list-users",
            workspace=workspace,
            actor=actor,
            timeout=timeout,
        )
        return list(resp.users)

    async def create_api_key(self, workspace, key, actor="",
                             timeout=IAM_TIMEOUT):
        """Create an API key.  ``key`` is an ``ApiKeyInput``.  Returns
        ``(plaintext, record)`` — plaintext is returned once and the
        caller is responsible for surfacing it to the operator."""
        resp = await self._request(
            operation="create-api-key",
            workspace=workspace,
            actor=actor,
            key=key,
            timeout=timeout,
        )
        return resp.api_key_plaintext, resp.api_key

    async def list_api_keys(self, workspace, user_id, actor="",
                            timeout=IAM_TIMEOUT):
        resp = await self._request(
            operation="list-api-keys",
            workspace=workspace,
            actor=actor,
            user_id=user_id,
            timeout=timeout,
        )
        return list(resp.api_keys)

    async def revoke_api_key(self, workspace, key_id, actor="",
                             timeout=IAM_TIMEOUT):
        await self._request(
            operation="revoke-api-key",
            workspace=workspace,
            actor=actor,
            key_id=key_id,
            timeout=timeout,
        )

    async def login(self, username, password, workspace="",
                    timeout=IAM_TIMEOUT):
        """Validate credentials and return ``(jwt, expires_iso)``.
        ``workspace`` is optional; defaults at the server to the
        OSS default workspace."""
        resp = await self._request(
            operation="login",
            workspace=workspace,
            username=username,
            password=password,
            timeout=timeout,
        )
        return resp.jwt, resp.jwt_expires

    async def get_signing_key_public(self, timeout=IAM_TIMEOUT):
        """Return the active JWT signing public key in PEM.  The
        gateway calls this at startup and caches the result."""
        resp = await self._request(
            operation="get-signing-key-public",
            timeout=timeout,
        )
        return resp.signing_key_public

    async def change_password(self, user_id, current_password,
                              new_password, timeout=IAM_TIMEOUT):
        await self._request(
            operation="change-password",
            user_id=user_id,
            password=current_password,
            new_password=new_password,
            timeout=timeout,
        )

    async def reset_password(self, workspace, user_id, actor="",
                             timeout=IAM_TIMEOUT):
        """Admin-driven password reset.  Returns the plaintext
        temporary password (returned once)."""
        resp = await self._request(
            operation="reset-password",
            workspace=workspace,
            actor=actor,
            user_id=user_id,
            timeout=timeout,
        )
        return resp.temporary_password

    async def get_user(self, workspace, user_id, actor="",
                       timeout=IAM_TIMEOUT):
        resp = await self._request(
            operation="get-user",
            workspace=workspace,
            actor=actor,
            user_id=user_id,
            timeout=timeout,
        )
        return resp.user

    async def update_user(self, workspace, user_id, user, actor="",
                          timeout=IAM_TIMEOUT):
        resp = await self._request(
            operation="update-user",
            workspace=workspace,
            actor=actor,
            user_id=user_id,
            user=user,
            timeout=timeout,
        )
        return resp.user

    async def disable_user(self, workspace, user_id, actor="",
                           timeout=IAM_TIMEOUT):
        await self._request(
            operation="disable-user",
            workspace=workspace,
            actor=actor,
            user_id=user_id,
            timeout=timeout,
        )

    async def enable_user(self, workspace, user_id, actor="",
                          timeout=IAM_TIMEOUT):
        await self._request(
            operation="enable-user",
            workspace=workspace,
            actor=actor,
            user_id=user_id,
            timeout=timeout,
        )

    async def delete_user(self, workspace, user_id, actor="",
                          timeout=IAM_TIMEOUT):
        await self._request(
            operation="delete-user",
            workspace=workspace,
            actor=actor,
            user_id=user_id,
            timeout=timeout,
        )

    async def create_workspace(self, workspace_record, actor="",
                               timeout=IAM_TIMEOUT):
        resp = await self._request(
            operation="create-workspace",
            actor=actor,
            workspace_record=workspace_record,
            timeout=timeout,
        )
        return resp.workspace

    async def list_workspaces(self, actor="", timeout=IAM_TIMEOUT):
        resp = await self._request(
            operation="list-workspaces",
            actor=actor,
            timeout=timeout,
        )
        return list(resp.workspaces)

    async def get_workspace(self, workspace_id, actor="",
                            timeout=IAM_TIMEOUT):
        from ..schema import WorkspaceInput
        resp = await self._request(
            operation="get-workspace",
            actor=actor,
            workspace_record=WorkspaceInput(id=workspace_id),
            timeout=timeout,
        )
        return resp.workspace

    async def update_workspace(self, workspace_record, actor="",
                               timeout=IAM_TIMEOUT):
        resp = await self._request(
            operation="update-workspace",
            actor=actor,
            workspace_record=workspace_record,
            timeout=timeout,
        )
        return resp.workspace

    async def disable_workspace(self, workspace_id, actor="",
                                timeout=IAM_TIMEOUT):
        from ..schema import WorkspaceInput
        await self._request(
            operation="disable-workspace",
            actor=actor,
            workspace_record=WorkspaceInput(id=workspace_id),
            timeout=timeout,
        )

    async def rotate_signing_key(self, actor="", timeout=IAM_TIMEOUT):
        await self._request(
            operation="rotate-signing-key",
            actor=actor,
            timeout=timeout,
        )


class IamClientSpec(RequestResponseSpec):
    def __init__(self, request_name, response_name):
        super().__init__(
            request_name=request_name,
            request_schema=IamRequest,
            response_name=response_name,
            response_schema=IamResponse,
            impl=IamClient,
        )
