"""
IAM-backed authentication for the API gateway.

Replaces the legacy GATEWAY_SECRET shared-token Authenticator.  The
gateway is now stateless with respect to credentials: it either
verifies a JWT locally using the active IAM signing public key, or
resolves an API key by hash with a short local cache backed by the
IAM service.

Identity returned by authenticate() is the (user_id, workspace,
roles) triple the rest of the gateway — capability checks, workspace
resolver, audit logging — needs.
"""

import asyncio
import base64
import hashlib
import json
import logging
import time
import uuid
from dataclasses import dataclass

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


@dataclass
class Identity:
    user_id: str
    workspace: str
    roles: list
    source: str   # "api-key" | "jwt"


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

    async def start(self, max_retries=30, retry_delay=2.0):
        """Fetch the signing public key from IAM.  Retries on
        failure — the gateway may be starting before IAM is ready."""

        async def _fetch(client):
            return await client.get_signing_key_public()

        for attempt in range(max_retries):
            try:
                pem = await self._with_client(_fetch)
                if pem:
                    self._signing_public_pem = pem
                    logger.info(
                        "IamAuth: fetched IAM signing public key "
                        f"({len(pem)} bytes)"
                    )
                    return
            except Exception as e:
                logger.info(
                    f"IamAuth: waiting for IAM signing key "
                    f"({type(e).__name__}: {e}); "
                    f"retry {attempt + 1}/{max_retries}"
                )
            await asyncio.sleep(retry_delay)

        # Don't prevent startup forever.  A later authenticate() call
        # will try again via the JWT path.
        logger.warning(
            "IamAuth: could not fetch IAM signing key at startup; "
            "JWT validation will fail until it's available"
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

        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            raise _auth_failure()
        token = header[len("Bearer "):].strip()
        if not token:
            raise _auth_failure()

        # API keys always start with "tg_".  JWTs have two dots and
        # no "tg_" prefix.  Discriminate cheaply.
        if token.startswith("tg_"):
            return await self._resolve_api_key(token)
        if token.count(".") == 2:
            return self._verify_jwt(token)
        raise _auth_failure()

    def _verify_jwt(self, token):
        if not self._signing_public_pem:
            raise _auth_failure()
        try:
            claims = _verify_jwt_eddsa(token, self._signing_public_pem)
        except Exception as e:
            logger.debug(f"JWT validation failed: {type(e).__name__}: {e}")
            raise _auth_failure()

        sub = claims.get("sub", "")
        ws = claims.get("workspace", "")
        roles = list(claims.get("roles", []))
        if not sub or not ws:
            raise _auth_failure()

        return Identity(
            user_id=sub, workspace=ws, roles=roles, source="jwt",
        )

    async def _resolve_api_key(self, plaintext):
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
                    return await client.resolve_api_key(plaintext)
                user_id, workspace, roles = await self._with_client(_call)
            except Exception as e:
                logger.debug(
                    f"API key resolution failed: "
                    f"{type(e).__name__}: {e}"
                )
                raise _auth_failure()

            if not user_id or not workspace:
                raise _auth_failure()

            identity = Identity(
                user_id=user_id, workspace=workspace,
                roles=list(roles), source="api-key",
            )
            self._key_cache[h] = (identity, now + API_KEY_CACHE_TTL)
            return identity
