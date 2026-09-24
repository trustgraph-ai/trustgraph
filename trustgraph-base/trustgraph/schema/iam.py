
from dataclasses import dataclass, field

from .core.topic import queue
from .core.primitives import Error

############################################################################

# IAM service — see docs/tech-specs/iam-protocol.md for the full protocol.

@dataclass
class UserInput:
    username: str = ""
    name: str = ""
    email: str = ""
    # Only populated on create-user; never on update-user.
    password: str = ""
    roles: list[str] = field(default_factory=list)
    enabled: bool = True
    must_change_password: bool = False


@dataclass
class UserRecord:
    id: str = ""
    default_workspace: str = ""
    username: str = ""
    name: str = ""
    email: str = ""
    roles: list[str] = field(default_factory=list)
    enabled: bool = True
    must_change_password: bool = False
    created: str = ""


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
    created: str = ""


@dataclass
class ApiKeyInput:
    user_id: str = ""
    name: str = ""
    expires: str = ""


@dataclass
class ApiKeyRecord:
    id: str = ""
    user_id: str = ""
    name: str = ""
    prefix: str = ""
    expires: str = ""
    created: str = ""
    last_used: str = ""


# ---- Enterprise IAM types (additive) ----

@dataclass
class GroupInput:
    name: str = ""
    description: str = ""
    enabled: bool = True


@dataclass
class GrantInput:
    capability: str = ""
    workspace: str = ""


@dataclass
class IamRequest:
    operation: str = ""

    workspace: str = ""
    actor: str = ""

    user_id: str = ""
    username: str = ""
    key_id: str = ""
    api_key: str = ""

    password: str = ""
    new_password: str = ""

    user: UserInput | None = None
    workspace_record: WorkspaceInput | None = None
    key: ApiKeyInput | None = None

    # ---- Enterprise IAM inputs (additive) ----
    group_id: str = ""
    member_type: str = ""
    member_id: str = ""
    group: GroupInput | None = None
    grant: GrantInput | None = None

    # ---- Audit context (informational, echoed into audit events) ----
    request_id: str = ""
    client_ip: str = ""

    # ---- authorise / authorise-many inputs ----
    capability: str = ""
    resource_json: str = ""
    parameters_json: str = ""
    authorise_checks: str = ""


@dataclass
class IamResponse:
    user: UserRecord | None = None
    users: list[UserRecord] = field(default_factory=list)

    workspace: WorkspaceRecord | None = None
    workspaces: list[WorkspaceRecord] = field(default_factory=list)

    api_key_plaintext: str = ""
    api_key: ApiKeyRecord | None = None
    api_keys: list[ApiKeyRecord] = field(default_factory=list)

    # login, rotate-signing-key
    jwt: str = ""
    jwt_expires: str = ""

    # get-signing-key-public
    signing_key_public: str = ""

    # resolve-api-key
    resolved_user_id: str = ""
    resolved_default_workspace: str = ""
    resolved_roles: list[str] = field(default_factory=list)

    # reset-password
    temporary_password: str = ""

    # bootstrap
    bootstrap_admin_user_id: str = ""
    bootstrap_admin_api_key: str = ""

    bootstrap_available: bool = False

    # ---- authorise / authorise-many outputs ----
    decision_allow: bool = False
    decision_ttl_seconds: int = 0
    decisions_json: str = ""

    # ---- Enterprise IAM outputs (additive) ----
    group_json: str = ""
    groups_json: str = ""
    members_json: str = ""
    grants_json: str = ""
    effective_permissions_json: str = ""

    error: Error | None = None


iam_request_queue = queue('iam', cls='request')
iam_response_queue = queue('iam', cls='response')

############################################################################
