
from dataclasses import dataclass, field

from ..core.topic import queue
from ..core.primitives import Error

############################################################################

# IAM service — see docs/tech-specs/iam-protocol.md for the full protocol.
#
# Transport: request/response pub/sub, correlated by the `id` message
# property.  Caller is the API gateway only; the IAM service trusts
# the bus per the enforcement-boundary policy (no per-request auth
# against the caller).


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
    workspace: str = ""
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
    # First 4 chars of the plaintext token, for operator identification
    # in list-api-keys.  Never enough to reconstruct the key.
    prefix: str = ""
    expires: str = ""
    created: str = ""
    last_used: str = ""


@dataclass
class IamRequest:
    operation: str = ""

    # Workspace scope.  Required on workspace-scoped operations;
    # omitted for system-level ops (workspace CRUD, signing-key
    # ops, bootstrap, resolve-api-key, login).
    workspace: str = ""

    # Acting user id for audit.  Empty for internal-origin and for
    # operations that resolve an identity (login, resolve-api-key).
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

    # ---- authorise / authorise-many inputs ----
    # Capability string from the vocabulary in capabilities.md.
    capability: str = ""
    # Resource identifier as JSON.  See the IAM contract spec for
    # the resource-component vocabulary.  An empty dict denotes a
    # system-level resource.
    resource_json: str = ""
    # Operation parameters as JSON.  Decision-relevant fields the
    # operation supplied that are not part of the resource address
    # (e.g. workspace association on create-user).
    parameters_json: str = ""
    # For authorise-many: a JSON-serialised list of
    # {"capability": str, "resource": dict, "parameters": dict}.
    authorise_checks: str = ""


@dataclass
class IamResponse:
    user: UserRecord | None = None
    users: list[UserRecord] = field(default_factory=list)

    workspace: WorkspaceRecord | None = None
    workspaces: list[WorkspaceRecord] = field(default_factory=list)

    # create-api-key returns the plaintext once; never populated
    # on any other operation.
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
    resolved_workspace: str = ""
    resolved_roles: list[str] = field(default_factory=list)

    # reset-password
    temporary_password: str = ""

    # bootstrap
    bootstrap_admin_user_id: str = ""
    bootstrap_admin_api_key: str = ""

    # bootstrap-status — true iff iam-svc is in 'bootstrap' mode with
    # empty tables, i.e. an unconsumed bootstrap call would succeed.
    bootstrap_available: bool = False

    # ---- authorise / authorise-many outputs ----
    # authorise: the regime's allow / deny verdict.
    decision_allow: bool = False
    # Cache TTL the regime suggests, in seconds.  Gateway respects
    # this for both allow and deny decisions; bounded above by
    # gateway-side policy (typically <= 60s).
    decision_ttl_seconds: int = 0
    # authorise-many: a JSON-serialised list of {"allow": bool,
    # "ttl": int} in the same order as the request's
    # authorise_checks.
    decisions_json: str = ""

    error: Error | None = None


iam_request_queue = queue('iam', cls='request')
iam_response_queue = queue('iam', cls='response')

############################################################################
