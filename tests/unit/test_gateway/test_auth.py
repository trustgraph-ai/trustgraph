"""
Tests for gateway/auth.py — IamAuth, JWT verification, API key
resolution cache.

JWTs are signed with real Ed25519 keypairs generated per-test, so
the crypto path is exercised end-to-end without mocks.  API-key
resolution is tested against a stubbed IamClient since the real
one requires pub/sub.
"""

import base64
import json
import time
from unittest.mock import AsyncMock, Mock, patch

import pytest
from aiohttp import web
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from trustgraph.gateway.auth import (
    IamAuth, Identity,
    _b64url_decode, _verify_jwt_eddsa,
    API_KEY_CACHE_TTL,
)


# -- helpers ---------------------------------------------------------------


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def make_keypair():
    priv = ed25519.Ed25519PrivateKey.generate()
    public_pem = priv.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")
    return priv, public_pem


def sign_jwt(priv, claims, alg="EdDSA"):
    header = {"alg": alg, "typ": "JWT", "kid": "kid-test"}
    h = _b64url(json.dumps(header, separators=(",", ":"), sort_keys=True).encode())
    p = _b64url(json.dumps(claims, separators=(",", ":"), sort_keys=True).encode())
    signing_input = f"{h}.{p}".encode("ascii")
    if alg == "EdDSA":
        sig = priv.sign(signing_input)
    else:
        raise ValueError(f"test helper doesn't sign {alg}")
    return f"{h}.{p}.{_b64url(sig)}"


def make_request(auth_header):
    """Minimal stand-in for an aiohttp request — IamAuth only reads
    ``request.headers["Authorization"]``."""
    req = Mock()
    req.headers = {}
    if auth_header is not None:
        req.headers["Authorization"] = auth_header
    return req


# -- pure helpers ----------------------------------------------------------


class TestB64UrlDecode:

    def test_round_trip_without_padding(self):
        data = b"hello"
        encoded = _b64url(data)
        assert _b64url_decode(encoded) == data

    def test_handles_various_lengths(self):
        for s in (b"a", b"ab", b"abc", b"abcd", b"abcde"):
            assert _b64url_decode(_b64url(s)) == s


# -- JWT verification -----------------------------------------------------


class TestVerifyJwtEddsa:

    def test_valid_jwt_passes(self):
        priv, pub = make_keypair()
        claims = {
            "sub": "user-1", "workspace": "default",
            "roles": ["reader"],
            "iat": int(time.time()),
            "exp": int(time.time()) + 60,
        }
        token = sign_jwt(priv, claims)
        got = _verify_jwt_eddsa(token, pub)
        assert got["sub"] == "user-1"
        assert got["workspace"] == "default"

    def test_expired_jwt_rejected(self):
        priv, pub = make_keypair()
        claims = {
            "sub": "user-1", "workspace": "default", "roles": [],
            "iat": int(time.time()) - 3600,
            "exp": int(time.time()) - 1,
        }
        token = sign_jwt(priv, claims)
        with pytest.raises(ValueError, match="expired"):
            _verify_jwt_eddsa(token, pub)

    def test_bad_signature_rejected(self):
        priv_a, _ = make_keypair()
        _, pub_b = make_keypair()
        claims = {
            "sub": "user-1", "workspace": "default", "roles": [],
            "iat": int(time.time()),
            "exp": int(time.time()) + 60,
        }
        token = sign_jwt(priv_a, claims)
        # pub_b never signed this token.
        with pytest.raises(Exception):
            _verify_jwt_eddsa(token, pub_b)

    def test_malformed_jwt_rejected(self):
        _, pub = make_keypair()
        with pytest.raises(ValueError, match="malformed"):
            _verify_jwt_eddsa("not-a-jwt", pub)

    def test_unsupported_algorithm_rejected(self):
        priv, pub = make_keypair()
        # Manually build an "alg":"HS256" header — no signer needed
        # since we expect it to bail before verifying.
        header = {"alg": "HS256", "typ": "JWT", "kid": "x"}
        payload = {
            "sub": "user-1", "workspace": "default", "roles": [],
            "iat": int(time.time()), "exp": int(time.time()) + 60,
        }
        h = _b64url(json.dumps(header, separators=(",", ":")).encode())
        p = _b64url(json.dumps(payload, separators=(",", ":")).encode())
        sig = _b64url(b"not-a-real-sig")
        token = f"{h}.{p}.{sig}"
        with pytest.raises(ValueError, match="unsupported alg"):
            _verify_jwt_eddsa(token, pub)


# -- Identity --------------------------------------------------------------


class TestIdentity:

    def test_fields(self):
        i = Identity(
            user_id="u", workspace="w", roles=["reader"], source="api-key",
        )
        assert i.user_id == "u"
        assert i.workspace == "w"
        assert i.roles == ["reader"]
        assert i.source == "api-key"


# -- IamAuth.authenticate --------------------------------------------------


class TestIamAuthDispatch:
    """``authenticate()`` chooses between the JWT and API-key paths
    by shape of the bearer."""

    @pytest.mark.asyncio
    async def test_no_authorization_header_raises_401(self):
        auth = IamAuth(backend=Mock())
        with pytest.raises(web.HTTPUnauthorized):
            await auth.authenticate(make_request(None))

    @pytest.mark.asyncio
    async def test_non_bearer_header_raises_401(self):
        auth = IamAuth(backend=Mock())
        with pytest.raises(web.HTTPUnauthorized):
            await auth.authenticate(make_request("Basic whatever"))

    @pytest.mark.asyncio
    async def test_empty_bearer_raises_401(self):
        auth = IamAuth(backend=Mock())
        with pytest.raises(web.HTTPUnauthorized):
            await auth.authenticate(make_request("Bearer "))

    @pytest.mark.asyncio
    async def test_unknown_format_raises_401(self):
        # Not tg_... and not dotted-JWT shape.
        auth = IamAuth(backend=Mock())
        with pytest.raises(web.HTTPUnauthorized):
            await auth.authenticate(make_request("Bearer garbage"))

    @pytest.mark.asyncio
    async def test_valid_jwt_resolves_to_identity(self):
        priv, pub = make_keypair()
        claims = {
            "sub": "user-1", "workspace": "default",
            "roles": ["writer"],
            "iat": int(time.time()),
            "exp": int(time.time()) + 60,
        }
        token = sign_jwt(priv, claims)

        auth = IamAuth(backend=Mock())
        auth._signing_public_pem = pub

        ident = await auth.authenticate(
            make_request(f"Bearer {token}")
        )
        assert ident.user_id == "user-1"
        assert ident.workspace == "default"
        assert ident.roles == ["writer"]
        assert ident.source == "jwt"

    @pytest.mark.asyncio
    async def test_jwt_without_public_key_fails(self):
        # If the gateway hasn't fetched IAM's public key yet, JWTs
        # must not validate — even ones that would otherwise pass.
        priv, _ = make_keypair()
        claims = {
            "sub": "user-1", "workspace": "default", "roles": [],
            "iat": int(time.time()), "exp": int(time.time()) + 60,
        }
        token = sign_jwt(priv, claims)
        auth = IamAuth(backend=Mock())
        # _signing_public_pem defaults to None
        with pytest.raises(web.HTTPUnauthorized):
            await auth.authenticate(make_request(f"Bearer {token}"))

    @pytest.mark.asyncio
    async def test_api_key_path(self):
        auth = IamAuth(backend=Mock())

        async def fake_resolve(api_key):
            assert api_key == "tg_testkey"
            return ("user-xyz", "default", ["admin"])

        async def fake_with_client(op):
            return await op(Mock(resolve_api_key=fake_resolve))

        with patch.object(auth, "_with_client", side_effect=fake_with_client):
            ident = await auth.authenticate(
                make_request("Bearer tg_testkey")
            )
        assert ident.user_id == "user-xyz"
        assert ident.workspace == "default"
        assert ident.roles == ["admin"]
        assert ident.source == "api-key"

    @pytest.mark.asyncio
    async def test_api_key_rejection_masked_as_401(self):
        auth = IamAuth(backend=Mock())

        async def fake_with_client(op):
            raise RuntimeError("auth-failed: unknown api key")

        with patch.object(auth, "_with_client", side_effect=fake_with_client):
            with pytest.raises(web.HTTPUnauthorized):
                await auth.authenticate(
                    make_request("Bearer tg_bogus")
                )


# -- API key cache ---------------------------------------------------------


class TestApiKeyCache:

    @pytest.mark.asyncio
    async def test_cache_hit_skips_iam(self):
        auth = IamAuth(backend=Mock())
        calls = {"n": 0}

        async def fake_with_client(op):
            calls["n"] += 1
            return await op(Mock(
                resolve_api_key=AsyncMock(
                    return_value=("u", "default", ["reader"]),
                )
            ))

        with patch.object(auth, "_with_client", side_effect=fake_with_client):
            await auth.authenticate(make_request("Bearer tg_k1"))
            await auth.authenticate(make_request("Bearer tg_k1"))
            await auth.authenticate(make_request("Bearer tg_k1"))

        # Only the first lookup reaches IAM; the rest are cache hits.
        assert calls["n"] == 1

    @pytest.mark.asyncio
    async def test_different_keys_are_separately_cached(self):
        auth = IamAuth(backend=Mock())
        seen = []

        async def fake_with_client(op):
            async def resolve(plaintext):
                seen.append(plaintext)
                return ("u-" + plaintext, "default", ["reader"])
            return await op(Mock(resolve_api_key=resolve))

        with patch.object(auth, "_with_client", side_effect=fake_with_client):
            a = await auth.authenticate(make_request("Bearer tg_a"))
            b = await auth.authenticate(make_request("Bearer tg_b"))

        assert a.user_id == "u-tg_a"
        assert b.user_id == "u-tg_b"
        assert seen == ["tg_a", "tg_b"]

    @pytest.mark.asyncio
    async def test_cache_has_ttl_constant_set(self):
        # Not a behaviour test — just ensures we don't accidentally
        # set TTL to 0 (which would defeat the cache) or to a week.
        assert 10 <= API_KEY_CACHE_TTL <= 3600
