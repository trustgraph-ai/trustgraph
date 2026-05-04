"""
IAM business logic.  Handles ``IamRequest`` messages and builds
``IamResponse`` messages.  Does not concern itself with transport.

See docs/tech-specs/iam-protocol.md for the wire-level contract and
docs/tech-specs/iam.md for the surrounding architecture.
"""

import asyncio
import base64
import datetime
import hashlib
import json
import logging
import os
import secrets
import uuid

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from trustgraph.schema import (
    IamResponse, Error,
    UserRecord, WorkspaceRecord, ApiKeyRecord,
)

from ... tables.iam import IamTableStore

logger = logging.getLogger(__name__)


DEFAULT_WORKSPACE = "default"
BOOTSTRAP_ADMIN_USERNAME = "admin"
BOOTSTRAP_ADMIN_NAME = "Administrator"

PBKDF2_ITERATIONS = 600_000
API_KEY_PREFIX = "tg_"
API_KEY_RANDOM_BYTES = 24

JWT_ISSUER = "trustgraph-iam"
JWT_TTL_SECONDS = 3600

# Default authorisation cache TTL the regime tells the gateway to
# observe.  60s is the OSS-spec maximum revocation latency: a role
# change, workspace disable, or key revoke takes effect within at
# most this much time.
AUTHZ_CACHE_TTL_SECONDS = 60


# OSS regime role table.  Lives here, not in the gateway — the
# gateway is regime-agnostic and must not encode policy.
#
# Each role has a capability set and a workspace scope.  The
# evaluator (handle_authorise below) checks (a) that some role
# held by the caller grants the requested capability, and (b)
# that role's workspace scope permits the target workspace.

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


def _scope_permits(role_scope, target_workspace, assigned_workspace):
    """Does the given role apply to ``target_workspace``?"""
    if role_scope == "*":
        return True
    if role_scope == "assigned":
        return target_workspace == assigned_workspace
    return False


def _now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _now_dt():
    return datetime.datetime.now(datetime.timezone.utc)


def _iso(dt):
    if dt is None:
        return ""
    if isinstance(dt, str):
        return dt
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt.isoformat()


def _hash_password(password):
    """Return an encoded PBKDF2-SHA-256 hash of ``password``.

    Format: ``pbkdf2-sha256$<iters>$<b64-salt>$<b64-hash>``.  Stored
    verbatim in the password_hash column so the algorithm and cost
    can be evolved later (new rows get a new prefix; old rows are
    verified with their own parameters).
    """
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS,
    )
    return (
        f"pbkdf2-sha256${PBKDF2_ITERATIONS}"
        f"${base64.b64encode(salt).decode('ascii')}"
        f"${base64.b64encode(dk).decode('ascii')}"
    )


def _verify_password(password, encoded):
    """Constant-time verify ``password`` against an encoded hash."""
    try:
        algo, iters, b64_salt, b64_hash = encoded.split("$")
    except ValueError:
        return False
    if algo != "pbkdf2-sha256":
        return False
    try:
        iters = int(iters)
        salt = base64.b64decode(b64_salt)
        target = base64.b64decode(b64_hash)
    except Exception:
        return False
    dk = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iters,
    )
    return secrets.compare_digest(dk, target)


def _generate_api_key():
    """Return a fresh API-key plaintext of the form ``tg_<random>``."""
    return API_KEY_PREFIX + secrets.token_urlsafe(API_KEY_RANDOM_BYTES)


def _hash_api_key(plaintext):
    """SHA-256 hex digest of an API key plaintext.  Used as the
    primary key in ``iam_api_keys`` so ``resolve-api-key`` is O(1)."""
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()


def _err(type, message):
    return IamResponse(error=Error(type=type, message=message))


def _parse_expires(s):
    if not s:
        return None
    try:
        return datetime.datetime.fromisoformat(s)
    except Exception:
        return None


def _b64url(data):
    """URL-safe base64 encode without padding, as required by JWT."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _generate_signing_keypair():
    """Return (kid, private_pem, public_pem) for a fresh Ed25519
    keypair.  Ed25519 / EdDSA: small (32-byte public key), fast,
    deterministic, side-channel-resistant by construction, free of
    NIST-curve baggage."""
    key = ed25519.Ed25519PrivateKey.generate()
    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("ascii")
    public_pem = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")
    kid = uuid.uuid4().hex[:16]
    return kid, private_pem, public_pem


def _sign_jwt(kid, private_pem, claims):
    """Produce a compact-serialisation EdDSA (Ed25519) JWT for
    ``claims``."""
    key = serialization.load_pem_private_key(
        private_pem.encode("ascii"), password=None,
    )
    if not isinstance(key, ed25519.Ed25519PrivateKey):
        raise RuntimeError(
            f"signing key is not Ed25519: {type(key).__name__}"
        )

    header = {"alg": "EdDSA", "typ": "JWT", "kid": kid}
    header_b = _b64url(json.dumps(
        header, separators=(",", ":"), sort_keys=True,
    ).encode("utf-8"))
    payload_b = _b64url(json.dumps(
        claims, separators=(",", ":"), sort_keys=True,
    ).encode("utf-8"))
    signing_input = f"{header_b}.{payload_b}".encode("ascii")
    signature = key.sign(signing_input)

    return f"{header_b}.{payload_b}.{_b64url(signature)}"


class IamService:

    def __init__(self, host, username, password, keyspace,
                 bootstrap_mode, bootstrap_token=None,
                 on_workspace_created=None, on_workspace_deleted=None):
        self.table_store = IamTableStore(
            host, username, password, keyspace,
        )
        # bootstrap_mode: "token" or "bootstrap".  In "token" mode the
        # service auto-seeds on first start using the provided
        # bootstrap_token and the ``bootstrap`` operation is refused
        # thereafter (indistinguishable from an already-bootstrapped
        # deployment per the error policy).  In "bootstrap" mode the
        # ``bootstrap`` operation is live until tables are populated.
        if bootstrap_mode not in ("token", "bootstrap"):
            raise ValueError(
                f"bootstrap_mode must be 'token' or 'bootstrap', "
                f"got {bootstrap_mode!r}"
            )
        if bootstrap_mode == "token" and not bootstrap_token:
            raise ValueError(
                "bootstrap_mode='token' requires bootstrap_token"
            )
        self.bootstrap_mode = bootstrap_mode
        self.bootstrap_token = bootstrap_token

        # Callbacks for workspace lifecycle events.  Called after the
        # workspace is created/deleted in IAM's own store so that the
        # processor can announce it via the config service.
        self._on_workspace_created = on_workspace_created
        self._on_workspace_deleted = on_workspace_deleted

        self._signing_key = None
        self._signing_key_lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    async def handle(self, v):
        op = v.operation

        try:
            if op == "bootstrap":
                return await self.handle_bootstrap(v)
            if op == "bootstrap-status":
                return await self.handle_bootstrap_status(v)
            if op == "whoami":
                return await self.handle_whoami(v)
            if op == "resolve-api-key":
                return await self.handle_resolve_api_key(v)
            if op == "create-user":
                return await self.handle_create_user(v)
            if op == "list-users":
                return await self.handle_list_users(v)
            if op == "create-api-key":
                return await self.handle_create_api_key(v)
            if op == "list-api-keys":
                return await self.handle_list_api_keys(v)
            if op == "revoke-api-key":
                return await self.handle_revoke_api_key(v)
            if op == "login":
                return await self.handle_login(v)
            if op == "get-signing-key-public":
                return await self.handle_get_signing_key_public(v)
            if op == "change-password":
                return await self.handle_change_password(v)
            if op == "reset-password":
                return await self.handle_reset_password(v)
            if op == "get-user":
                return await self.handle_get_user(v)
            if op == "update-user":
                return await self.handle_update_user(v)
            if op == "disable-user":
                return await self.handle_disable_user(v)
            if op == "enable-user":
                return await self.handle_enable_user(v)
            if op == "delete-user":
                return await self.handle_delete_user(v)
            if op == "create-workspace":
                return await self.handle_create_workspace(v)
            if op == "list-workspaces":
                return await self.handle_list_workspaces(v)
            if op == "get-workspace":
                return await self.handle_get_workspace(v)
            if op == "update-workspace":
                return await self.handle_update_workspace(v)
            if op == "disable-workspace":
                return await self.handle_disable_workspace(v)
            if op == "rotate-signing-key":
                return await self.handle_rotate_signing_key(v)
            if op == "authorise":
                return await self.handle_authorise(v)
            if op == "authorise-many":
                return await self.handle_authorise_many(v)

            return _err(
                "invalid-argument",
                f"unknown or not-yet-implemented operation: {op!r}",
            )

        except Exception as e:
            logger.error(
                f"IAM {op} failed: {type(e).__name__}: {e}",
                exc_info=True,
            )
            return _err("internal-error", str(e))

    # ------------------------------------------------------------------
    # Record conversion
    # ------------------------------------------------------------------

    def _row_to_user_record(self, row):
        (
            id, workspace, username, name, email, _password_hash,
            roles, enabled, must_change_password, created,
        ) = row
        return UserRecord(
            id=id or "",
            workspace=workspace or "",
            username=username or "",
            name=name or "",
            email=email or "",
            roles=sorted(roles) if roles else [],
            enabled=bool(enabled),
            must_change_password=bool(must_change_password),
            created=_iso(created),
        )

    def _row_to_api_key_record(self, row):
        (
            _key_hash, id, user_id, name, prefix, expires,
            created, last_used,
        ) = row
        return ApiKeyRecord(
            id=id or "",
            user_id=user_id or "",
            name=name or "",
            prefix=prefix or "",
            expires=_iso(expires),
            created=_iso(created),
            last_used=_iso(last_used),
        )

    # ------------------------------------------------------------------
    # bootstrap
    # ------------------------------------------------------------------

    async def auto_bootstrap_if_token_mode(self):
        """Called from the service processor at startup.  In
        ``token`` mode, if tables are empty, seeds the default
        workspace / admin / signing key using the operator-provided
        bootstrap token.  The admin's API key plaintext is *the*
        ``bootstrap_token`` — the operator already knows it, nothing
        needs to be returned or logged.

        In ``bootstrap`` mode this is a no-op; seeding happens on
        explicit ``bootstrap`` operation invocation."""
        if self.bootstrap_mode != "token":
            return

        if await self.table_store.any_workspace_exists():
            logger.info(
                "IAM: token mode, tables already populated; skipping "
                "auto-bootstrap"
            )
            return

        logger.info("IAM: token mode, empty tables; auto-bootstrapping")
        await self._seed_tables(self.bootstrap_token)
        logger.info(
            "IAM: auto-bootstrap complete using operator-provided token"
        )

    async def _seed_tables(self, api_key_plaintext):
        """Shared seeding logic used by token-mode auto-bootstrap and
        bootstrap-mode handle_bootstrap.  Creates the default
        workspace, admin user, admin API key (using the given
        plaintext), and an initial signing key.  Returns the admin
        user id."""
        now = _now_dt()

        await self.table_store.put_workspace(
            id=DEFAULT_WORKSPACE,
            name="Default",
            enabled=True,
            created=now,
        )

        if self._on_workspace_created:
            await self._on_workspace_created(DEFAULT_WORKSPACE)

        admin_user_id = str(uuid.uuid4())
        admin_password = secrets.token_urlsafe(32)
        await self.table_store.put_user(
            id=admin_user_id,
            workspace=DEFAULT_WORKSPACE,
            username=BOOTSTRAP_ADMIN_USERNAME,
            name=BOOTSTRAP_ADMIN_NAME,
            email="",
            password_hash=_hash_password(admin_password),
            roles=["admin"],
            enabled=True,
            must_change_password=True,
            created=now,
        )

        key_id = str(uuid.uuid4())
        await self.table_store.put_api_key(
            key_hash=_hash_api_key(api_key_plaintext),
            id=key_id,
            user_id=admin_user_id,
            name="bootstrap",
            prefix=api_key_plaintext[:len(API_KEY_PREFIX) + 4],
            expires=None,
            created=now,
            last_used=None,
        )

        kid, private_pem, public_pem = _generate_signing_keypair()
        await self.table_store.put_signing_key(
            kid=kid,
            private_pem=private_pem,
            public_pem=public_pem,
            created=now,
            retired=None,
        )
        self._signing_key = (kid, private_pem, public_pem)

        logger.info(
            f"IAM seeded: workspace={DEFAULT_WORKSPACE!r}, "
            f"admin user_id={admin_user_id}, signing key kid={kid}"
        )
        return admin_user_id

    async def handle_bootstrap(self, v):
        """Explicit bootstrap op.  Only available in ``bootstrap``
        mode and only when tables are empty.  Every other case is
        masked to a generic auth failure — the caller cannot
        distinguish 'not in bootstrap mode' from 'already
        bootstrapped' from 'operation forbidden'."""
        if self.bootstrap_mode != "bootstrap":
            return _err("auth-failed", "auth failure")

        if await self.table_store.any_workspace_exists():
            return _err("auth-failed", "auth failure")

        plaintext = _generate_api_key()
        admin_user_id = await self._seed_tables(plaintext)

        return IamResponse(
            bootstrap_admin_user_id=admin_user_id,
            bootstrap_admin_api_key=plaintext,
        )

    async def handle_whoami(self, v):
        """Return the caller's own user record.  ``v.actor`` is the
        authenticated identity's handle (the gateway populates it
        from ``identity.handle``).  No ``users:read`` capability
        required — every authenticated user can read themselves."""
        if not v.actor:
            return _err(
                "invalid-argument",
                "actor required (gateway should populate this)",
            )
        user_row = await self.table_store.get_user(v.actor)
        if user_row is None:
            return _err("not-found", "user not found")
        return IamResponse(user=self._row_to_user_record(user_row))

    async def handle_bootstrap_status(self, v):
        """Probe op: returns whether the deployment is currently in
        the unconsumed-bootstrap state (i.e. ``bootstrap`` mode with
        empty tables, where an explicit ``bootstrap`` call would
        succeed).  PUBLIC so a UI can decide whether to render the
        first-run setup flow without invoking the side-effectful
        ``bootstrap`` op.

        The information leaked is intentionally narrow: an empty
        deployment in bootstrap mode is already inferable (no users,
        no logins succeed); this just makes the answer explicit
        instead of forcing callers to probe the masked-failure path."""
        available = (
            self.bootstrap_mode == "bootstrap"
            and not await self.table_store.any_workspace_exists()
        )
        return IamResponse(bootstrap_available=available)

    # ------------------------------------------------------------------
    # Signing key helpers
    # ------------------------------------------------------------------

    async def _get_active_signing_key(self):
        """Return ``(kid, private_pem, public_pem)`` for the active
        signing key.  Loads from Cassandra on first call.  Generates
        and persists a new key if none exists — covers the case where
        ``login`` is called before ``bootstrap`` (shouldn't happen in
        practice but keeps the service internally consistent)."""
        if self._signing_key is not None:
            return self._signing_key

        async with self._signing_key_lock:
            if self._signing_key is not None:
                return self._signing_key

            rows = await self.table_store.list_signing_keys()
            active = [r for r in rows if r[4] is None]

            if active:
                row = active[0]
                self._signing_key = (row[0], row[1], row[2])
                logger.info(
                    f"IAM: loaded active signing key kid={row[0]}"
                )
                return self._signing_key

            kid, private_pem, public_pem = _generate_signing_keypair()
            await self.table_store.put_signing_key(
                kid=kid,
                private_pem=private_pem,
                public_pem=public_pem,
                created=_now_dt(),
                retired=None,
            )
            self._signing_key = (kid, private_pem, public_pem)
            logger.info(
                f"IAM: generated active signing key kid={kid} "
                f"(no existing key found)"
            )
            return self._signing_key

    # ------------------------------------------------------------------
    # login
    # ------------------------------------------------------------------

    async def handle_login(self, v):
        if not v.username:
            return _err("auth-failed", "username required")
        if not v.password:
            return _err("auth-failed", "password required")

        # Login accepts an optional workspace parameter.  If omitted
        # we use the default workspace (OSS single-workspace
        # assumption).  Multi-workspace enterprise editions swap in a
        # resolver that looks across the caller's permitted set.
        workspace = v.workspace or DEFAULT_WORKSPACE

        user_id = await self.table_store.get_user_id_by_username(
            workspace, v.username,
        )
        if not user_id:
            return _err("auth-failed", "no such user")

        user_row = await self.table_store.get_user(user_id)
        if user_row is None:
            return _err("auth-failed", "user disappeared")

        (
            id, ws, _username, _name, _email, password_hash,
            _roles, enabled, _mcp, _created,
        ) = user_row

        if not enabled:
            return _err("auth-failed", "user disabled")
        if not password_hash or not _verify_password(
                v.password, password_hash,
        ):
            return _err("auth-failed", "bad credentials")

        ws_row = await self.table_store.get_workspace(ws)
        if ws_row is None or not ws_row[2]:
            return _err("auth-failed", "workspace disabled")

        kid, private_pem, _ = await self._get_active_signing_key()

        now_ts = int(_now_dt().timestamp())
        exp_ts = now_ts + JWT_TTL_SECONDS
        # Per the IAM contract the gateway never reads policy state
        # from the credential — roles stay server-side, reachable
        # only via authorise().  JWT carries identity + workspace
        # binding only.
        claims = {
            "iss": JWT_ISSUER,
            "sub": id,
            "workspace": ws,
            "iat": now_ts,
            "exp": exp_ts,
        }
        token = _sign_jwt(kid, private_pem, claims)

        expires_iso = datetime.datetime.fromtimestamp(
            exp_ts, tz=datetime.timezone.utc,
        ).isoformat()

        return IamResponse(jwt=token, jwt_expires=expires_iso)

    # ------------------------------------------------------------------
    # get-signing-key-public
    # ------------------------------------------------------------------

    async def handle_get_signing_key_public(self, v):
        _, _, public_pem = await self._get_active_signing_key()
        return IamResponse(signing_key_public=public_pem)

    # ------------------------------------------------------------------
    # Record-conversion helper for workspaces
    # ------------------------------------------------------------------

    def _row_to_workspace_record(self, row):
        id, name, enabled, created = row
        return WorkspaceRecord(
            id=id or "",
            name=name or "",
            enabled=bool(enabled),
            created=_iso(created),
        )

    async def _resolve_user(self, user_id, workspace=None):
        """Return (user_row, error_response_or_None).  Loads the user
        record by id and (when ``workspace`` is supplied) verifies the
        record's home workspace matches.

        Workspace is an *optional integrity check* — the user record
        is system-level, identified by id alone.  If the caller asserts
        a workspace, we verify; if they omit it, we just return the
        record.  Authorisation (whether the caller is permitted to
        operate on this user) is the gateway's responsibility via the
        contract's ``authorise`` call before the handler is reached.
        """
        user_row = await self.table_store.get_user(user_id)
        if user_row is None:
            return None, _err("not-found", "user not found")
        if workspace and user_row[1] != workspace:
            return None, _err(
                "operation-not-permitted",
                "user is in a different workspace",
            )
        return user_row, None

    # ------------------------------------------------------------------
    # change-password
    # ------------------------------------------------------------------

    async def handle_change_password(self, v):
        if not v.user_id:
            return _err("invalid-argument", "user_id required")
        if not v.password:
            return _err("invalid-argument", "password (current) required")
        if not v.new_password:
            return _err("invalid-argument", "new_password required")

        user_row = await self.table_store.get_user(v.user_id)
        if user_row is None:
            return _err("auth-failed", "no such user")

        _id, _ws, _un, _name, _email, password_hash, _r, enabled, _mcp, _c = (
            user_row
        )
        if not enabled:
            return _err("auth-failed", "user disabled")
        if not password_hash or not _verify_password(
                v.password, password_hash,
        ):
            return _err("auth-failed", "bad credentials")

        await self.table_store.update_user_password(
            id=v.user_id,
            password_hash=_hash_password(v.new_password),
            must_change_password=False,
        )
        return IamResponse()

    # ------------------------------------------------------------------
    # reset-password
    # ------------------------------------------------------------------

    async def handle_reset_password(self, v):
        if not v.user_id:
            return _err("invalid-argument", "user_id required")

        _, err = await self._resolve_user(v.user_id, v.workspace or None)
        if err is not None:
            return err

        temporary = secrets.token_urlsafe(12)
        await self.table_store.update_user_password(
            id=v.user_id,
            password_hash=_hash_password(temporary),
            must_change_password=True,
        )
        return IamResponse(temporary_password=temporary)

    # ------------------------------------------------------------------
    # get-user / update-user / disable-user
    # ------------------------------------------------------------------

    async def handle_get_user(self, v):
        if not v.user_id:
            return _err("invalid-argument", "user_id required")

        user_row, err = await self._resolve_user(
            v.user_id, v.workspace or None,
        )
        if err is not None:
            return err
        return IamResponse(user=self._row_to_user_record(user_row))

    async def handle_update_user(self, v):
        """Update user profile fields: name, email, roles, enabled,
        must_change_password.  Username is immutable — change it by
        creating a new user and disabling the old one.  Password
        changes go through change-password / reset-password."""
        if not v.user_id:
            return _err("invalid-argument", "user_id required")
        if v.user is None:
            return _err("invalid-argument", "user field required")
        if v.user.password:
            return _err(
                "invalid-argument",
                "password cannot be changed via update-user; "
                "use change-password or reset-password",
            )

        existing, err = await self._resolve_user(
            v.user_id, v.workspace or None,
        )
        if err is not None:
            return err
        if v.user.username and v.user.username != existing[2]:
            return _err(
                "invalid-argument",
                "username is immutable; create a new user instead",
            )

        # Carry forward fields the caller didn't provide.
        (
            _id, _ws, _username, cur_name, cur_email, _pw,
            cur_roles, cur_enabled, cur_mcp, _created,
        ) = existing

        new_name = v.user.name if v.user.name else cur_name
        new_email = v.user.email if v.user.email else cur_email
        new_roles = list(v.user.roles) if v.user.roles else list(
            cur_roles or [],
        )
        new_enabled = v.user.enabled if v.user.enabled is not None else (
            cur_enabled
        )
        new_mcp = (
            v.user.must_change_password
            if v.user.must_change_password is not None
            else cur_mcp
        )

        await self.table_store.update_user_profile(
            id=v.user_id,
            name=new_name,
            email=new_email,
            roles=new_roles,
            enabled=new_enabled,
            must_change_password=new_mcp,
        )

        updated = await self.table_store.get_user(v.user_id)
        return IamResponse(user=self._row_to_user_record(updated))

    async def handle_disable_user(self, v):
        """Soft-delete: set enabled=false and revoke every API key
        belonging to the user."""
        if not v.user_id:
            return _err("invalid-argument", "user_id required")

        _, err = await self._resolve_user(v.user_id, v.workspace or None)
        if err is not None:
            return err

        await self.table_store.update_user_enabled(
            id=v.user_id, enabled=False,
        )

        # Revoke all their API keys.
        key_rows = await self.table_store.list_api_keys_by_user(v.user_id)
        for kr in key_rows:
            await self.table_store.delete_api_key(kr[0])

        return IamResponse()

    async def handle_enable_user(self, v):
        """Re-enable a previously disabled user.  Does not restore
        API keys — those have to be re-issued by the admin."""
        if not v.user_id:
            return _err("invalid-argument", "user_id required")

        _, err = await self._resolve_user(v.user_id, v.workspace or None)
        if err is not None:
            return err

        await self.table_store.update_user_enabled(
            id=v.user_id, enabled=True,
        )
        return IamResponse()

    async def handle_delete_user(self, v):
        """Hard-delete a user.  Removes the ``iam_users`` row, the
        ``iam_users_by_username`` lookup row, and every API key
        belonging to the user.

        Unlike disable, this frees the username for re-use and
        removes the user's personal data from storage (intended to
        cover GDPR erasure-style requirements).  When audit logging
        lands, the decision to delete vs. anonymise referenced audit
        rows will need to be revisited."""
        if not v.user_id:
            return _err("invalid-argument", "user_id required")

        user_row, err = await self._resolve_user(
            v.user_id, v.workspace or None,
        )
        if err is not None:
            return err

        # user_row indices match get_user columns.  Username is [2].
        username = user_row[2]
        record_workspace = user_row[1]

        # Revoke all API keys.
        key_rows = await self.table_store.list_api_keys_by_user(v.user_id)
        for kr in key_rows:
            await self.table_store.delete_api_key(kr[0])

        # Remove username lookup — keyed on (workspace, username),
        # so use the resolved workspace from the user record rather
        # than relying on the caller-supplied filter.
        if username:
            await self.table_store.delete_username_lookup(
                record_workspace, username,
            )

        # Remove user record.
        await self.table_store.delete_user(v.user_id)

        return IamResponse()

    # ------------------------------------------------------------------
    # Workspace CRUD
    # ------------------------------------------------------------------

    async def handle_create_workspace(self, v):
        if v.workspace_record is None or not v.workspace_record.id:
            return _err(
                "invalid-argument",
                "workspace_record.id required for create-workspace",
            )
        if v.workspace_record.id.startswith("_"):
            return _err(
                "invalid-argument",
                "workspace ids beginning with '_' are reserved",
            )

        existing = await self.table_store.get_workspace(
            v.workspace_record.id,
        )
        if existing is not None:
            return _err("duplicate", "workspace already exists")

        now = _now_dt()
        await self.table_store.put_workspace(
            id=v.workspace_record.id,
            name=v.workspace_record.name or v.workspace_record.id,
            enabled=v.workspace_record.enabled,
            created=now,
        )

        if self._on_workspace_created:
            await self._on_workspace_created(v.workspace_record.id)

        row = await self.table_store.get_workspace(v.workspace_record.id)
        return IamResponse(workspace=self._row_to_workspace_record(row))

    async def handle_list_workspaces(self, v):
        rows = await self.table_store.list_workspaces()
        return IamResponse(
            workspaces=[
                self._row_to_workspace_record(r) for r in rows
            ],
        )

    async def handle_get_workspace(self, v):
        if v.workspace_record is None or not v.workspace_record.id:
            return _err("invalid-argument", "workspace_record.id required")
        row = await self.table_store.get_workspace(v.workspace_record.id)
        if row is None:
            return _err("not-found", "workspace not found")
        return IamResponse(workspace=self._row_to_workspace_record(row))

    async def handle_update_workspace(self, v):
        """Update workspace name / enabled.  The id is immutable."""
        if v.workspace_record is None or not v.workspace_record.id:
            return _err("invalid-argument", "workspace_record.id required")
        row = await self.table_store.get_workspace(v.workspace_record.id)
        if row is None:
            return _err("not-found", "workspace not found")

        _, cur_name, cur_enabled, _created = row
        new_name = (
            v.workspace_record.name
            if v.workspace_record.name else cur_name
        )
        new_enabled = (
            v.workspace_record.enabled
            if v.workspace_record.enabled is not None
            else cur_enabled
        )

        await self.table_store.update_workspace(
            id=v.workspace_record.id,
            name=new_name,
            enabled=new_enabled,
        )
        updated = await self.table_store.get_workspace(
            v.workspace_record.id,
        )
        return IamResponse(
            workspace=self._row_to_workspace_record(updated),
        )

    async def handle_disable_workspace(self, v):
        """Set enabled=false, disable every user in the workspace,
        revoke every API key belonging to those users."""
        if v.workspace_record is None or not v.workspace_record.id:
            return _err("invalid-argument", "workspace_record.id required")

        row = await self.table_store.get_workspace(v.workspace_record.id)
        if row is None:
            return _err("not-found", "workspace not found")

        await self.table_store.update_workspace(
            id=v.workspace_record.id,
            name=row[1] or v.workspace_record.id,
            enabled=False,
        )

        user_rows = await self.table_store.list_users_by_workspace(
            v.workspace_record.id,
        )
        for ur in user_rows:
            user_id = ur[0]
            await self.table_store.update_user_enabled(
                id=user_id, enabled=False,
            )
            key_rows = await self.table_store.list_api_keys_by_user(user_id)
            for kr in key_rows:
                await self.table_store.delete_api_key(kr[0])

        if self._on_workspace_deleted:
            await self._on_workspace_deleted(v.workspace_record.id)

        return IamResponse()

    # ------------------------------------------------------------------
    # rotate-signing-key
    # ------------------------------------------------------------------

    async def handle_rotate_signing_key(self, v):
        """Create a new Ed25519 signing key, retire the current
        active key, switch the in-memory cache over.

        The retired key row is kept in ``iam_signing_keys`` so the
        gateway's JWT validator can continue to validate previously-
        issued tokens during the grace period.  Actual grace-period
        enforcement (time-window acceptance at the validator) lands
        with the gateway auth middleware work."""

        # Retire the currently-active key, if any.
        current = await self._get_active_signing_key()
        now = _now_dt()
        if current is not None:
            cur_kid, _cur_priv, _cur_pub = current
            await self.table_store.retire_signing_key(
                kid=cur_kid, retired=now,
            )

        new_kid, new_priv, new_pub = _generate_signing_keypair()
        await self.table_store.put_signing_key(
            kid=new_kid,
            private_pem=new_priv,
            public_pem=new_pub,
            created=now,
            retired=None,
        )
        self._signing_key = (new_kid, new_priv, new_pub)
        logger.info(
            f"IAM: rotated signing key.  "
            f"New kid={new_kid}, retired kid={(current or (None,))[0]}"
        )
        return IamResponse()

    # ------------------------------------------------------------------
    # resolve-api-key
    # ------------------------------------------------------------------

    async def handle_resolve_api_key(self, v):
        if not v.api_key:
            return _err("auth-failed", "no api key")

        row = await self.table_store.get_api_key_by_hash(
            _hash_api_key(v.api_key),
        )
        if row is None:
            return _err("auth-failed", "unknown api key")

        (
            _key_hash, _id, user_id, _name, _prefix, expires,
            _created, _last_used,
        ) = row

        if expires is not None:
            exp_dt = expires
            if isinstance(exp_dt, str):
                exp_dt = datetime.datetime.fromisoformat(exp_dt)
            if exp_dt.tzinfo is None:
                exp_dt = exp_dt.replace(tzinfo=datetime.timezone.utc)
            if exp_dt < _now_dt():
                return _err("auth-failed", "api key expired")

        user_row = await self.table_store.get_user(user_id)
        if user_row is None:
            return _err("auth-failed", "owning user missing")
        user = self._row_to_user_record(user_row)
        if not user.enabled:
            return _err("auth-failed", "owning user disabled")

        # Workspace-disabled check.
        ws_row = await self.table_store.get_workspace(user.workspace)
        if ws_row is None or not ws_row[2]:
            return _err("auth-failed", "owning workspace disabled")

        return IamResponse(
            resolved_user_id=user.id,
            resolved_workspace=user.workspace,
            resolved_roles=list(user.roles),
        )

    # ------------------------------------------------------------------
    # create-user
    # ------------------------------------------------------------------

    async def handle_create_user(self, v):
        if not v.workspace:
            return _err(
                "invalid-argument", "workspace required for create-user",
            )
        if v.user is None:
            return _err(
                "invalid-argument", "user field required for create-user",
            )
        if not v.user.username:
            return _err("invalid-argument", "user.username required")
        if not v.user.password:
            return _err("invalid-argument", "user.password required")

        # Workspace must exist and be enabled.
        ws = await self.table_store.get_workspace(v.workspace)
        if ws is None or not ws[2]:
            return _err("not-found", "workspace not found or disabled")

        # Uniqueness on username within workspace.
        existing = await self.table_store.get_user_id_by_username(
            v.workspace, v.user.username,
        )
        if existing:
            return _err("duplicate", "username already exists")

        user_id = str(uuid.uuid4())
        now = _now_dt()

        await self.table_store.put_user(
            id=user_id,
            workspace=v.workspace,
            username=v.user.username,
            name=v.user.name or v.user.username,
            email=v.user.email or "",
            password_hash=_hash_password(v.user.password),
            roles=list(v.user.roles or []),
            enabled=v.user.enabled,
            must_change_password=v.user.must_change_password,
            created=now,
        )

        row = await self.table_store.get_user(user_id)
        return IamResponse(user=self._row_to_user_record(row))

    # ------------------------------------------------------------------
    # list-users
    # ------------------------------------------------------------------

    async def handle_list_users(self, v):
        # System-level operation: workspace, when supplied, is a
        # filter on the user record's home-workspace association.
        # Empty workspace returns the deployment-wide list — the
        # gateway has already authorised the caller's authority to
        # see that scope.
        if v.workspace:
            rows = await self.table_store.list_users_by_workspace(v.workspace)
        else:
            rows = await self.table_store.list_users()
        return IamResponse(
            users=[self._row_to_user_record(r) for r in rows],
        )

    # ------------------------------------------------------------------
    # create-api-key
    # ------------------------------------------------------------------

    async def handle_create_api_key(self, v):
        if v.key is None or not v.key.user_id:
            return _err("invalid-argument", "key.user_id required")
        if not v.key.name:
            return _err("invalid-argument", "key.name required")

        # API keys are system-level records with a workspace
        # association (the user's home workspace).  Workspace is an
        # optional integrity check on the caller's request — when
        # supplied it must match the target user's home workspace;
        # when omitted, the user's home workspace is used.
        user_row, err = await self._resolve_user(
            v.key.user_id, v.workspace or None,
        )
        if err is not None:
            return err

        plaintext = _generate_api_key()
        key_id = str(uuid.uuid4())
        now = _now_dt()
        expires_dt = _parse_expires(v.key.expires)

        await self.table_store.put_api_key(
            key_hash=_hash_api_key(plaintext),
            id=key_id,
            user_id=v.key.user_id,
            name=v.key.name,
            prefix=plaintext[:len(API_KEY_PREFIX) + 4],
            expires=expires_dt,
            created=now,
            last_used=None,
        )

        row = await self.table_store.get_api_key_by_hash(
            _hash_api_key(plaintext),
        )
        return IamResponse(
            api_key_plaintext=plaintext,
            api_key=self._row_to_api_key_record(row),
        )

    # ------------------------------------------------------------------
    # list-api-keys
    # ------------------------------------------------------------------

    async def handle_list_api_keys(self, v):
        if not v.user_id:
            return _err(
                "invalid-argument", "user_id required for list-api-keys",
            )

        # Workspace is an optional integrity check.
        _, err = await self._resolve_user(v.user_id, v.workspace or None)
        if err is not None:
            return err

        rows = await self.table_store.list_api_keys_by_user(v.user_id)
        return IamResponse(
            api_keys=[self._row_to_api_key_record(r) for r in rows],
        )

    # ------------------------------------------------------------------
    # revoke-api-key
    # ------------------------------------------------------------------

    async def handle_revoke_api_key(self, v):
        if not v.key_id:
            return _err("invalid-argument", "key_id required")

        row = await self.table_store.get_api_key_by_id(v.key_id)
        if row is None:
            return _err("not-found", "api key not found")

        key_hash, _id, user_id, _name, _prefix, _expires, _c, _lu = row

        # Workspace is an optional integrity check via the owning user.
        if v.workspace:
            user_row = await self.table_store.get_user(user_id)
            if user_row is None or user_row[1] != v.workspace:
                return _err(
                    "operation-not-permitted",
                    "key belongs to a different workspace",
                )

        await self.table_store.delete_api_key(key_hash)
        return IamResponse()

    # ------------------------------------------------------------------
    # authorise / authorise-many
    #
    # The IAM contract (see docs/tech-specs/iam-contract.md) calls
    # for the regime — not the gateway — to decide whether an
    # identity may perform a capability on a resource given the
    # operation's parameters.  These two operations are the OSS
    # regime's implementation of that contract.
    #
    # Inputs (on IamRequest):
    #   user_id          — the identity handle (the gateway's
    #                       opaque reference).  For OSS this is the
    #                       user record's id.
    #   capability       — the capability string from the
    #                       capabilities.md vocabulary.
    #   resource_json    — JSON dict, the resource address
    #                       ({} for system, {workspace} for
    #                       workspace, {workspace, flow} for flow).
    #   parameters_json  — JSON dict, decision-relevant operation
    #                       parameters (e.g. workspace association
    #                       on user-registry operations).
    #   authorise_checks — for authorise-many, a JSON list of
    #                       {capability, resource, parameters}.
    #
    # Outputs (on IamResponse):
    #   decision_allow         — single allow / deny verdict.
    #   decision_ttl_seconds   — gateway cache TTL for this
    #                            decision.
    #   decisions_json         — for authorise-many, list of
    #                            {allow, ttl} in request order.
    # ------------------------------------------------------------------

    def _decide(self, user_row, capability, resource, parameters):
        """Single authorisation decision.  Returns (allow, ttl)."""

        if user_row is None:
            return False, AUTHZ_CACHE_TTL_SECONDS

        # user_row layout:
        # 0:id 1:workspace 2:username 3:name 4:email 5:password_hash
        # 6:roles 7:enabled 8:must_change_password 9:created
        if not user_row[7]:  # disabled
            return False, AUTHZ_CACHE_TTL_SECONDS

        # Disabled workspace check (defense in depth — credentials
        # bound to a disabled workspace shouldn't be able to act).
        # Cheap; one row read.
        # We do this only when a target workspace is involved, to
        # avoid an extra read for system-level operations that
        # bypass workspace altogether.
        target_workspace = (
            (resource or {}).get("workspace")
            or (parameters or {}).get("workspace")
        )

        roles = user_row[6] or set()
        assigned_workspace = user_row[1]

        for role_name in roles:
            defn = ROLE_DEFINITIONS.get(role_name)
            if defn is None:
                continue
            if capability not in defn["capabilities"]:
                continue
            if target_workspace is None or _scope_permits(
                    defn["workspace_scope"],
                    target_workspace,
                    assigned_workspace,
            ):
                return True, AUTHZ_CACHE_TTL_SECONDS

        return False, AUTHZ_CACHE_TTL_SECONDS

    async def handle_authorise(self, v):
        if not v.capability:
            return _err("invalid-argument", "capability required")
        if not v.user_id:
            return _err("invalid-argument", "user_id (handle) required")

        try:
            resource = json.loads(v.resource_json or "{}")
            parameters = json.loads(v.parameters_json or "{}")
        except json.JSONDecodeError as e:
            return _err("invalid-argument", f"bad json: {e}")

        user_row = await self.table_store.get_user(v.user_id)
        allow, ttl = self._decide(
            user_row, v.capability, resource, parameters,
        )
        return IamResponse(
            decision_allow=allow,
            decision_ttl_seconds=ttl,
        )

    async def handle_authorise_many(self, v):
        if not v.user_id:
            return _err("invalid-argument", "user_id (handle) required")
        if not v.authorise_checks:
            return _err("invalid-argument", "authorise_checks required")

        try:
            checks = json.loads(v.authorise_checks)
        except json.JSONDecodeError as e:
            return _err("invalid-argument", f"bad json: {e}")
        if not isinstance(checks, list):
            return _err(
                "invalid-argument",
                "authorise_checks must be a JSON list",
            )

        # One user lookup for the whole batch.
        user_row = await self.table_store.get_user(v.user_id)

        decisions = []
        for c in checks:
            if not isinstance(c, dict):
                decisions.append({
                    "allow": False,
                    "ttl": AUTHZ_CACHE_TTL_SECONDS,
                })
                continue
            allow, ttl = self._decide(
                user_row,
                c.get("capability", ""),
                c.get("resource") or {},
                c.get("parameters") or {},
            )
            decisions.append({"allow": allow, "ttl": ttl})

        return IamResponse(decisions_json=json.dumps(decisions))
