"""
Tests for user_context extraction from JWT claims in gateway auth.

Verifies that the gateway correctly extracts user_context from minted
JWTs into Identity, and that non-dict or absent user_context values
are handled safely.
"""

import base64
import json
import time
from unittest.mock import Mock, patch

import pytest
from aiohttp import web
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from trustgraph.gateway.auth import IamAuth, Identity


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def make_keypair():
    priv = ed25519.Ed25519PrivateKey.generate()
    public_pem = priv.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")
    return priv, public_pem


def sign_jwt(priv, claims):
    header = {"alg": "EdDSA", "typ": "JWT", "kid": "kid-test"}
    h = _b64url(json.dumps(header, separators=(",", ":"), sort_keys=True).encode())
    p = _b64url(json.dumps(claims, separators=(",", ":"), sort_keys=True).encode())
    signing_input = f"{h}.{p}".encode("ascii")
    sig = priv.sign(signing_input)
    return f"{h}.{p}.{_b64url(sig)}"


def make_request(token):
    req = Mock()
    req.headers = {"Authorization": f"Bearer {token}"}
    return req


USER_CONTEXT = {
    "user_id": "alice",
    "roles": ["analyst"],
    "organisational_units": ["research"],
    "purpose": "quarterly review",
}


class TestJwtUserContextExtraction:

    @pytest.mark.asyncio
    async def test_jwt_with_user_context_populates_identity(self):
        priv, pub = make_keypair()
        claims = {
            "sub": "alice",
            "default_workspace": "default",
            "user_context": USER_CONTEXT,
            "iat": int(time.time()),
            "exp": int(time.time()) + 60,
        }
        token = sign_jwt(priv, claims)

        auth = IamAuth(backend=Mock())
        auth._signing_public_pem = pub

        ident = await auth.authenticate(make_request(token))
        assert ident.user_context == USER_CONTEXT
        assert ident.handle == "alice"
        assert ident.source == "jwt"

    @pytest.mark.asyncio
    async def test_jwt_without_user_context_gives_none(self):
        priv, pub = make_keypair()
        claims = {
            "sub": "bob",
            "default_workspace": "default",
            "iat": int(time.time()),
            "exp": int(time.time()) + 60,
        }
        token = sign_jwt(priv, claims)

        auth = IamAuth(backend=Mock())
        auth._signing_public_pem = pub

        ident = await auth.authenticate(make_request(token))
        assert ident.user_context is None

    @pytest.mark.asyncio
    async def test_non_dict_user_context_ignored(self):
        priv, pub = make_keypair()
        claims = {
            "sub": "bob",
            "default_workspace": "default",
            "user_context": "not-a-dict",
            "iat": int(time.time()),
            "exp": int(time.time()) + 60,
        }
        token = sign_jwt(priv, claims)

        auth = IamAuth(backend=Mock())
        auth._signing_public_pem = pub

        ident = await auth.authenticate(make_request(token))
        assert ident.user_context is None

    @pytest.mark.asyncio
    async def test_list_user_context_ignored(self):
        priv, pub = make_keypair()
        claims = {
            "sub": "bob",
            "default_workspace": "default",
            "user_context": ["not", "a", "dict"],
            "iat": int(time.time()),
            "exp": int(time.time()) + 60,
        }
        token = sign_jwt(priv, claims)

        auth = IamAuth(backend=Mock())
        auth._signing_public_pem = pub

        ident = await auth.authenticate(make_request(token))
        assert ident.user_context is None

    @pytest.mark.asyncio
    async def test_null_user_context_gives_none(self):
        priv, pub = make_keypair()
        claims = {
            "sub": "bob",
            "default_workspace": "default",
            "user_context": None,
            "iat": int(time.time()),
            "exp": int(time.time()) + 60,
        }
        token = sign_jwt(priv, claims)

        auth = IamAuth(backend=Mock())
        auth._signing_public_pem = pub

        ident = await auth.authenticate(make_request(token))
        assert ident.user_context is None


class TestIdentityUserContextField:

    def test_default_is_none(self):
        ident = Identity(
            handle="u", default_workspace="w",
            principal_id="u", source="jwt",
        )
        assert ident.user_context is None

    def test_explicit_user_context(self):
        ident = Identity(
            handle="u", default_workspace="w",
            principal_id="u", source="jwt",
            user_context=USER_CONTEXT,
        )
        assert ident.user_context == USER_CONTEXT


class TestApiKeyIdentityHasNoUserContext:

    @pytest.mark.asyncio
    async def test_api_key_identity_user_context_is_none(self):
        auth = IamAuth(backend=Mock())

        async def fake_with_client(op):
            async def resolve(plaintext, **kwargs):
                return ("user-1", "default", ["admin"])
            return await op(Mock(resolve_api_key=resolve))

        with patch.object(auth, "_with_client", side_effect=fake_with_client):
            ident = await auth.authenticate(make_request("tg_testkey"))
        assert ident.user_context is None
        assert ident.source == "api-key"
