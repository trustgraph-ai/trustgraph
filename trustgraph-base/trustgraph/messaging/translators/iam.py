from typing import Dict, Any, Tuple

from ...schema import IamRequest, IamResponse
from ...schema import (
    UserInput, UserRecord,
    WorkspaceInput, WorkspaceRecord,
    ApiKeyInput, ApiKeyRecord,
)
from .base import MessageTranslator


def _user_input_from_dict(d):
    if d is None:
        return None
    return UserInput(
        username=d.get("username", ""),
        name=d.get("name", ""),
        email=d.get("email", ""),
        password=d.get("password", ""),
        roles=list(d.get("roles", [])),
        enabled=d.get("enabled", True),
        must_change_password=d.get("must_change_password", False),
    )


def _workspace_input_from_dict(d):
    if d is None:
        return None
    return WorkspaceInput(
        id=d.get("id", ""),
        name=d.get("name", ""),
        enabled=d.get("enabled", True),
    )


def _api_key_input_from_dict(d):
    if d is None:
        return None
    return ApiKeyInput(
        user_id=d.get("user_id", ""),
        name=d.get("name", ""),
        expires=d.get("expires", ""),
    )


def _user_record_to_dict(r):
    if r is None:
        return None
    return {
        "id": r.id,
        "workspace": r.workspace,
        "username": r.username,
        "name": r.name,
        "email": r.email,
        "roles": list(r.roles),
        "enabled": r.enabled,
        "must_change_password": r.must_change_password,
        "created": r.created,
    }


def _workspace_record_to_dict(r):
    if r is None:
        return None
    return {
        "id": r.id,
        "name": r.name,
        "enabled": r.enabled,
        "created": r.created,
    }


def _api_key_record_to_dict(r):
    if r is None:
        return None
    return {
        "id": r.id,
        "user_id": r.user_id,
        "name": r.name,
        "prefix": r.prefix,
        "expires": r.expires,
        "created": r.created,
        "last_used": r.last_used,
    }


class IamRequestTranslator(MessageTranslator):

    def decode(self, data: Dict[str, Any]) -> IamRequest:
        return IamRequest(
            operation=data.get("operation", ""),
            workspace=data.get("workspace", ""),
            actor=data.get("actor", ""),
            user_id=data.get("user_id", ""),
            username=data.get("username", ""),
            key_id=data.get("key_id", ""),
            api_key=data.get("api_key", ""),
            password=data.get("password", ""),
            new_password=data.get("new_password", ""),
            user=_user_input_from_dict(data.get("user")),
            workspace_record=_workspace_input_from_dict(
                data.get("workspace_record")
            ),
            key=_api_key_input_from_dict(data.get("key")),
        )

    def encode(self, obj: IamRequest) -> Dict[str, Any]:
        result = {"operation": obj.operation}
        for fname in (
                "workspace", "actor", "user_id", "username", "key_id",
                "api_key", "password", "new_password",
        ):
            v = getattr(obj, fname, "")
            if v:
                result[fname] = v
        if obj.user is not None:
            result["user"] = {
                "username": obj.user.username,
                "name": obj.user.name,
                "email": obj.user.email,
                "password": obj.user.password,
                "roles": list(obj.user.roles),
                "enabled": obj.user.enabled,
                "must_change_password": obj.user.must_change_password,
            }
        if obj.workspace_record is not None:
            result["workspace_record"] = {
                "id": obj.workspace_record.id,
                "name": obj.workspace_record.name,
                "enabled": obj.workspace_record.enabled,
            }
        if obj.key is not None:
            result["key"] = {
                "user_id": obj.key.user_id,
                "name": obj.key.name,
                "expires": obj.key.expires,
            }
        return result


class IamResponseTranslator(MessageTranslator):

    def decode(self, data: Dict[str, Any]) -> IamResponse:
        raise NotImplementedError(
            "IamResponse is a server-produced message; no HTTP→schema "
            "path is needed"
        )

    def encode(self, obj: IamResponse) -> Dict[str, Any]:
        result: Dict[str, Any] = {}

        if obj.user is not None:
            result["user"] = _user_record_to_dict(obj.user)
        if obj.users:
            result["users"] = [_user_record_to_dict(u) for u in obj.users]
        if obj.workspace is not None:
            result["workspace"] = _workspace_record_to_dict(obj.workspace)
        if obj.workspaces:
            result["workspaces"] = [
                _workspace_record_to_dict(w) for w in obj.workspaces
            ]
        if obj.api_key_plaintext:
            result["api_key_plaintext"] = obj.api_key_plaintext
        if obj.api_key is not None:
            result["api_key"] = _api_key_record_to_dict(obj.api_key)
        if obj.api_keys:
            result["api_keys"] = [
                _api_key_record_to_dict(k) for k in obj.api_keys
            ]
        if obj.jwt:
            result["jwt"] = obj.jwt
        if obj.jwt_expires:
            result["jwt_expires"] = obj.jwt_expires
        if obj.signing_key_public:
            result["signing_key_public"] = obj.signing_key_public
        if obj.resolved_user_id:
            result["resolved_user_id"] = obj.resolved_user_id
        if obj.resolved_workspace:
            result["resolved_workspace"] = obj.resolved_workspace
        if obj.resolved_roles:
            result["resolved_roles"] = list(obj.resolved_roles)
        if obj.temporary_password:
            result["temporary_password"] = obj.temporary_password
        if obj.bootstrap_admin_user_id:
            result["bootstrap_admin_user_id"] = obj.bootstrap_admin_user_id
        if obj.bootstrap_admin_api_key:
            result["bootstrap_admin_api_key"] = obj.bootstrap_admin_api_key
        # bootstrap-status: emit unconditionally — the false case is
        # meaningful for UIs deciding whether to render first-run
        # setup, so it can't be dropped by a truthy-only filter.
        result["bootstrap_available"] = bool(obj.bootstrap_available)

        return result

    def encode_with_completion(
            self, obj: IamResponse,
    ) -> Tuple[Dict[str, Any], bool]:
        return self.encode(obj), True
