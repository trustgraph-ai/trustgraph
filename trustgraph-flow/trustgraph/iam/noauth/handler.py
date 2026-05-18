"""
No-auth IAM handler.  Implements the IAM contract with every operation
returning a permissive or stub response.  No database, no crypto,
no state.
"""

import json
import logging

from trustgraph.schema import IamResponse, Error, UserRecord

logger = logging.getLogger(__name__)


def _err(type, message):
    return IamResponse(error=Error(type=type, message=message))


class NoAuthHandler:

    def __init__(self, default_user_id="anonymous",
                 default_workspace="default",
                 on_workspace_created=None):
        self.default_user_id = default_user_id
        self.default_workspace = default_workspace
        self._on_workspace_created = on_workspace_created

    def _default_identity_response(self):
        return IamResponse(
            resolved_user_id=self.default_user_id,
            resolved_workspace=self.default_workspace,
            resolved_roles=["admin"],
        )

    def _default_user_record(self):
        return UserRecord(
            id=self.default_user_id,
            workspace=self.default_workspace,
            username=self.default_user_id,
            name="Anonymous User",
            roles=["admin"],
            enabled=True,
        )

    async def handle(self, v):
        op = v.operation

        try:
            if op == "authenticate-anonymous":
                return self._default_identity_response()

            if op == "resolve-api-key":
                return self._default_identity_response()

            if op == "authorise":
                return IamResponse(
                    decision_allow=True,
                    decision_ttl_seconds=3600,
                )

            if op == "authorise-many":
                checks = json.loads(v.authorise_checks or "[]")
                decisions = [
                    {"allow": True, "ttl": 3600}
                    for _ in checks
                ]
                return IamResponse(
                    decisions_json=json.dumps(decisions),
                )

            if op == "get-signing-key-public":
                return IamResponse(signing_key_public="")

            if op == "bootstrap":
                return IamResponse()

            if op == "bootstrap-status":
                return IamResponse(bootstrap_available=False)

            if op == "whoami":
                return IamResponse(user=self._default_user_record())

            if op == "login":
                return IamResponse()

            if op in (
                "create-user", "get-user", "update-user",
                "disable-user", "enable-user",
            ):
                return IamResponse(user=self._default_user_record())

            if op == "list-users":
                return IamResponse(users=[self._default_user_record()])

            if op == "delete-user":
                return IamResponse()

            if op == "create-workspace":
                if self._on_workspace_created and v.workspace_record:
                    await self._on_workspace_created(v.workspace_record.id)
                return IamResponse()

            if op in (
                "get-workspace", "update-workspace",
                "disable-workspace",
            ):
                return IamResponse()

            if op == "list-workspaces":
                return IamResponse()

            if op in ("create-api-key", "list-api-keys", "revoke-api-key"):
                return IamResponse()

            if op in ("change-password", "reset-password"):
                return IamResponse()

            if op == "rotate-signing-key":
                return IamResponse()

            return _err(
                "invalid-argument",
                f"unknown operation: {op!r}",
            )

        except Exception as e:
            logger.error(
                f"no-auth {op} failed: {type(e).__name__}: {e}",
                exc_info=True,
            )
            return _err("internal-error", str(e))
