"""
IAM-backed authentication and authorisation for the API gateway.

The gateway delegates both authentication ("who is this caller?")
and authorisation ("may they do this?") to the IAM regime via the
contract specified in docs/tech-specs/iam-contract.md.  No regime-
specific policy (roles, scopes, claims) lives in the gateway.

- Authentication: API keys are resolved by IAM; JWTs are validated
  locally against the cached signing public key.
- Authorisation: every per-request decision is asked of IAM via
  ``authorise(identity, capability, resource, parameters)``, with
  results cached for the TTL the regime returns.
"""

import asyncio
import base64
import hashlib
import json
import logging
import time
import uuid
from dataclasses import dataclass, field

from aiohttp import web

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from ..base.iam_client import IamClient
from ..base.metrics import ProducerMetrics, SubscriberMetrics
from ..schema import (
    IamRequest, IamResponse,
    iam_request_queue, iam_response_queue,
)

logger = logging.getLogger("auth")

API_KEY_CACHE_TTL = 60  # seconds

# Upper bound on cache TTL the gateway honours for an authorisation
# decision, regardless of what the regime suggested.  Caps the
# revocation latency window.
AUTHZ_CACHE_TTL_MAX = 60  # seconds


@dataclass
class Identity:
    """The gateway-side surface of an authenticated caller.

    Per the IAM contract this is a small fixed shape; regime-internal
    state (roles, claims, group memberships) is reachable only via
    the regime's ``authorise`` operation.  The gateway itself never
    reads policy from this object.
    """
    # Opaque handle, quoted back when calling ``authorise``.  For
    # the OSS regime this is the user record's id; the gateway
    # treats it as a string with no semantic content.
    handle: str
    # The user's default workspace.  Used by the gateway as the
    # default-fill-in for operations that omit a workspace.  Not a
    # permission boundary — workspace access is controlled by the
    # IAM regime's authorise() decision, not by this field.
    default_workspace: str
    # Stable identifier for audit logs.  In OSS this is the same
    # value as ``handle``; not assumed equal in the contract.
    principal_id: str
    # How the credential was presented.  Non-policy; useful for
    # logs / metrics only.
    source: str   # "api-key" | "jwt" | "anonymous"


def _auth_failure():
    return web.HTTPUnauthorized(
        text='{"error":"auth failure"}',
        content_type="application/json",
    )


def _access_denied():
    return web.HTTPForbidden(
        text='{"error":"access denied"}',
        content_type="application/json",
    )


def _b64url_decode(s):
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def _verify_jwt_eddsa(token, public_pem):
    """Verify an Ed25519 JWT and return its claims.  Raises on any
    validation failure.  Refuses non-EdDSA algorithms."""
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("malformed JWT")
    h_b64, p_b64, s_b64 = parts
    signing_input = f"{h_b64}.{p_b64}".encode("ascii")
    header = json.loads(_b64url_decode(h_b64))
    if header.get("alg") != "EdDSA":
        raise ValueError(f"unsupported alg: {header.get('alg')!r}")

    key = serialization.load_pem_public_key(public_pem.encode("ascii"))
    if not isinstance(key, ed25519.Ed25519PublicKey):
        raise ValueError("public key is not Ed25519")

    signature = _b64url_decode(s_b64)
    key.verify(signature, signing_input)  # raises InvalidSignature

    claims = json.loads(_b64url_decode(p_b64))
    exp = claims.get("exp")
    if exp is None or exp < time.time():
        raise ValueError("expired")
    return claims


class IamAuth:
    """Resolves bearer credentials via the IAM service.

    Used by every gateway endpoint that needs authentication.  Fetches
    the IAM signing public key at startup (cached in memory).  API
    keys are resolved via the IAM service with a local hash→identity
    cache (short TTL so revoked keys stop working within the TTL
    window without any push mechanism)."""

    def __init__(self, backend, id="api-gateway"):
        self.backend = backend
        self.id = id

        # Populated at start() via IAM.
        self._signing_public_pem = None

        # API-key cache: plaintext_sha256_hex -> (Identity, expires_ts)
        self._key_cache = {}
        self._key_cache_lock = asyncio.Lock()

        # Authorisation decision cache: hash(handle, capability,
        # resource, parameters) -> (allow_bool, expires_ts).  Holds
        # both allows and denies — denies cached briefly to avoid
        # hammering iam-svc with repeated rejected attempts.
        self._authz_cache: dict[str, tuple[bool, float]] = {}
        self._authz_cache_lock = asyncio.Lock()

        # Known workspaces, maintained by the config receiver.
        # enforce_workspace checks this set to reject requests for
        # non-existent workspaces before routing to a queue that
        # has no consumer.
        self.known_workspaces: set[str] = set()

    # ------------------------------------------------------------------
    # Short-lived client helper.  Mirrors the pattern used by the
    # bootstrap framework and AsyncProcessor: a fresh uuid suffix per
    # invocation so Pulsar exclusive subscriptions don't collide with
    # ghosts from prior calls.
    # ------------------------------------------------------------------

    def _make_client(self):
        rr_id = str(uuid.uuid4())
        return IamClient(
            backend=self.backend,
            subscription=f"{self.id}--iam--{rr_id}",
            consumer_name=self.id,
            request_topic=iam_request_queue,
            request_schema=IamRequest,
            request_metrics=ProducerMetrics(
                processor=self.id, flow=None, name="iam-request",
            ),
            response_topic=iam_response_queue,
            response_schema=IamResponse,
            response_metrics=SubscriberMetrics(
                processor=self.id, flow=None, name="iam-response",
            ),
        )

    async def _with_client(self, op):
        """Open a short-lived IamClient, run ``op(client)``, close."""
        client = self._make_client()
        await client.start()
        try:
            return await op(client)
        finally:
            try:
                await client.stop()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def _fetch_signing_key(self):
        """Single attempt to fetch the IAM signing public key.
        Returns True on success."""
        try:
            async def _fetch(client):
                return await client.get_signing_key_public()

            pem = await self._with_client(_fetch)
            if pem:
                self._signing_public_pem = pem
                logger.info(
                    "IamAuth: fetched IAM signing public key "
                    f"({len(pem)} bytes)"
                )
                return True
        except Exception as e:
            logger.debug(
                f"IamAuth: signing key fetch failed: "
                f"{type(e).__name__}: {e}"
            )
        return False

    async def start(self, max_retries=30, retry_delay=2.0):
        """Fetch the signing public key from IAM.  Retries on
        failure — the gateway may be starting before IAM is ready."""

        for attempt in range(max_retries):
            if await self._fetch_signing_key():
                return
            logger.info(
                f"IamAuth: waiting for IAM signing key; "
                f"retry {attempt + 1}/{max_retries}"
            )
            await asyncio.sleep(retry_delay)

        logger.warning(
            "IamAuth: could not fetch IAM signing key at startup; "
            "JWT validation will retry on first request"
        )

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    async def authenticate(self, request):
        """Extract and validate the Bearer credential from an HTTP
        request.  Returns an ``Identity``.  Raises HTTPUnauthorized
        (401 / "auth failure") on any failure mode — the caller
        cannot distinguish missing / malformed / invalid / expired /
        revoked credentials."""

        request_id = request.get('audit_request_id', '') if hasattr(request, 'get') else ''
        client_ip = self._extract_client_ip(request)

        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            identity = await self._authenticate_anonymous(
                request_id=request_id, client_ip=client_ip,
            )
            self._annotate_request(request, identity)
            return identity
        token = header[len("Bearer "):].strip()
        if not token:
            identity = await self._authenticate_anonymous(
                request_id=request_id, client_ip=client_ip,
            )
            self._annotate_request(request, identity)
            return identity

        # API keys always start with "tg_".  JWTs have two dots and
        # no "tg_" prefix.  Discriminate cheaply.
        if token.startswith("tg_"):
            identity = await self._resolve_api_key(
                token, request_id=request_id, client_ip=client_ip,
            )
            self._annotate_request(request, identity)
            return identity
        if token.count(".") == 2:
            identity = await self._verify_jwt(token)
            self._annotate_request(request, identity)
            return identity
        raise _auth_failure()

    @staticmethod
    def _extract_client_ip(request):
        try:
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                return forwarded.split(",")[0].strip()
            return request.remote or ""
        except Exception:
            return ""

    @staticmethod
    def _annotate_request(request, identity):
        try:
            request['audit_identity'] = identity.principal_id
        except Exception:
            pass

    async def _verify_jwt(self, token):
        if not self._signing_public_pem:
            await self._fetch_signing_key()
        if not self._signing_public_pem:
            raise _auth_failure()
        try:
            claims = _verify_jwt_eddsa(token, self._signing_public_pem)
        except Exception as e:
            logger.debug(f"JWT validation failed: {type(e).__name__}: {e}")
            raise _auth_failure()

        sub = claims.get("sub", "")
        ws = claims.get("default_workspace", "")
        if not sub or not ws:
            raise _auth_failure()

        return Identity(
            handle=sub, default_workspace=ws,
            principal_id=sub, source="jwt",
        )

    async def _authenticate_anonymous(self, request_id="", client_ip=""):
        try:
            async def _call(client):
                return await client.authenticate_anonymous(
                    request_id=request_id, client_ip=client_ip,
                )
            user_id, default_workspace, _roles = await self._with_client(
                _call,
            )
        except Exception as e:
            logger.debug(
                f"Anonymous authentication rejected: "
                f"{type(e).__name__}: {e}"
            )
            raise _auth_failure()

        if not user_id or not default_workspace:
            raise _auth_failure()

        return Identity(
            handle=user_id, default_workspace=default_workspace,
            principal_id=user_id, source="anonymous",
        )

    async def _resolve_api_key(self, plaintext, request_id="", client_ip=""):
        h = hashlib.sha256(plaintext.encode("utf-8")).hexdigest()

        cached = self._key_cache.get(h)
        now = time.time()
        if cached and cached[1] > now:
            return cached[0]

        async with self._key_cache_lock:
            cached = self._key_cache.get(h)
            if cached and cached[1] > now:
                return cached[0]

            try:
                async def _call(client):
                    return await client.resolve_api_key(
                        plaintext, request_id=request_id,
                        client_ip=client_ip,
                    )
                # ``roles`` is returned by the OSS regime as a hint
                # but is not consulted by the gateway; all policy
                # decisions go through ``authorise``.
                user_id, default_workspace, _roles = await self._with_client(
                    _call,
                )
            except Exception as e:
                logger.debug(
                    f"API key resolution failed: "
                    f"{type(e).__name__}: {e}"
                )
                raise _auth_failure()

            if not user_id or not default_workspace:
                raise _auth_failure()

            identity = Identity(
                handle=user_id, default_workspace=default_workspace,
                principal_id=user_id, source="api-key",
            )
            self._key_cache[h] = (identity, now + API_KEY_CACHE_TTL)
            return identity

    # ------------------------------------------------------------------
    # Authorisation
    # ------------------------------------------------------------------

    @staticmethod
    def _authz_cache_key(handle, capability, resource, parameters):
        payload = json.dumps(
            {
                "h": handle,
                "c": capability,
                "r": resource or {},
                "p": parameters or {},
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    async def authorise(self, identity, capability, resource, parameters,
                        request_id="", client_ip=""):
        """Ask the IAM regime whether ``identity`` may perform
        ``capability`` on ``resource`` given ``parameters``.

        Caches the decision for the regime's suggested TTL, clamped
        above by ``AUTHZ_CACHE_TTL_MAX``.  Both allow and deny
        decisions are cached (denies briefly, to avoid hammering
        iam-svc with repeated rejected attempts).

        Raises ``HTTPForbidden`` (403 / "access denied") on a deny
        decision.  Raises ``HTTPUnauthorized`` (401 / "auth failure")
        if the IAM service errors out — failing closed."""

        key = self._authz_cache_key(
            identity.handle, capability, resource, parameters,
        )
        now = time.time()

        cached = self._authz_cache.get(key)
        if cached and cached[1] > now:
            allow, _ = cached
            if not allow:
                raise _access_denied()
            return

        async with self._authz_cache_lock:
            cached = self._authz_cache.get(key)
            if cached and cached[1] > now:
                allow, _ = cached
                if not allow:
                    raise _access_denied()
                return

            try:
                async def _call(client):
                    return await client.authorise(
                        identity.handle, capability,
                        resource or {}, parameters or {},
                        request_id=request_id, client_ip=client_ip,
                    )
                allow, ttl = await self._with_client(_call)
            except Exception as e:
                logger.warning(
                    f"authorise failed: {type(e).__name__}: {e}; "
                    f"failing closed for "
                    f"{identity.principal_id!r} cap={capability!r}"
                )
                raise _auth_failure()

            ttl = max(0, min(int(ttl or 0), AUTHZ_CACHE_TTL_MAX))
            self._authz_cache[key] = (bool(allow), now + ttl)

            if not allow:
                raise _access_denied()
            return
