"""
Tests for gateway/capabilities.py — the capability + role + workspace
model that underpins all gateway authorisation.
"""

import pytest
from aiohttp import web

from trustgraph.gateway.capabilities import (
    PUBLIC, AUTHENTICATED,
    KNOWN_CAPABILITIES, ROLE_DEFINITIONS,
    check, enforce_workspace, access_denied, auth_failure,
)


# -- test fixtures ---------------------------------------------------------


class _Identity:
    """Minimal stand-in for auth.Identity — the capability module
    accesses ``.workspace`` and ``.roles``."""
    def __init__(self, workspace, roles):
        self.user_id = "user-1"
        self.workspace = workspace
        self.roles = list(roles)


def reader_in(ws):
    return _Identity(ws, ["reader"])


def writer_in(ws):
    return _Identity(ws, ["writer"])


def admin_in(ws):
    return _Identity(ws, ["admin"])


# -- role table sanity -----------------------------------------------------


class TestRoleTable:

    def test_oss_roles_present(self):
        assert set(ROLE_DEFINITIONS.keys()) == {"reader", "writer", "admin"}

    def test_admin_is_cross_workspace(self):
        assert ROLE_DEFINITIONS["admin"]["workspace_scope"] == "*"

    def test_reader_writer_are_assigned_scope(self):
        assert ROLE_DEFINITIONS["reader"]["workspace_scope"] == "assigned"
        assert ROLE_DEFINITIONS["writer"]["workspace_scope"] == "assigned"

    def test_admin_superset_of_writer(self):
        admin = ROLE_DEFINITIONS["admin"]["capabilities"]
        writer = ROLE_DEFINITIONS["writer"]["capabilities"]
        assert writer.issubset(admin)

    def test_writer_superset_of_reader(self):
        writer = ROLE_DEFINITIONS["writer"]["capabilities"]
        reader = ROLE_DEFINITIONS["reader"]["capabilities"]
        assert reader.issubset(writer)

    def test_admin_has_users_admin(self):
        assert "users:admin" in ROLE_DEFINITIONS["admin"]["capabilities"]

    def test_writer_does_not_have_users_admin(self):
        assert "users:admin" not in ROLE_DEFINITIONS["writer"]["capabilities"]

    def test_every_bundled_capability_is_known(self):
        for role in ROLE_DEFINITIONS.values():
            for cap in role["capabilities"]:
                assert cap in KNOWN_CAPABILITIES


# -- check() ---------------------------------------------------------------


class TestCheck:

    def test_reader_has_reader_cap_in_own_workspace(self):
        assert check(reader_in("default"), "graph:read", "default")

    def test_reader_does_not_have_writer_cap(self):
        assert not check(reader_in("default"), "graph:write", "default")

    def test_reader_cannot_act_in_other_workspace(self):
        assert not check(reader_in("default"), "graph:read", "acme")

    def test_writer_has_write_in_own_workspace(self):
        assert check(writer_in("default"), "graph:write", "default")

    def test_writer_cannot_act_in_other_workspace(self):
        assert not check(writer_in("default"), "graph:write", "acme")

    def test_admin_has_everything_everywhere(self):
        for cap in ("graph:read", "graph:write", "config:write",
                    "users:admin", "metrics:read"):
            assert check(admin_in("default"), cap, "acme"), (
                f"admin should have {cap} in acme"
            )

    def test_admin_has_caps_without_explicit_workspace(self):
        assert check(admin_in("default"), "users:admin")

    def test_default_target_is_identity_workspace(self):
        # Reader with no target workspace → should check against own
        assert check(reader_in("default"), "graph:read")

    def test_unknown_capability_returns_false(self):
        assert not check(admin_in("default"), "nonsense:cap", "default")

    def test_unknown_role_contributes_nothing(self):
        ident = _Identity("default", ["made-up-role"])
        assert not check(ident, "graph:read", "default")

    def test_multi_role_union(self):
        # If a user is both reader and admin, they inherit admin's
        # cross-workspace powers.
        ident = _Identity("default", ["reader", "admin"])
        assert check(ident, "users:admin", "acme")


# -- enforce_workspace() ---------------------------------------------------


class TestEnforceWorkspace:

    def test_reader_in_own_workspace_allowed(self):
        data = {"workspace": "default", "operation": "x"}
        enforce_workspace(data, reader_in("default"))
        assert data["workspace"] == "default"

    def test_reader_no_workspace_injects_assigned(self):
        data = {"operation": "x"}
        enforce_workspace(data, reader_in("default"))
        assert data["workspace"] == "default"

    def test_reader_mismatched_workspace_denied(self):
        data = {"workspace": "acme", "operation": "x"}
        with pytest.raises(web.HTTPForbidden):
            enforce_workspace(data, reader_in("default"))

    def test_admin_can_target_any_workspace(self):
        data = {"workspace": "acme", "operation": "x"}
        enforce_workspace(data, admin_in("default"))
        assert data["workspace"] == "acme"

    def test_admin_no_workspace_defaults_to_assigned(self):
        data = {"operation": "x"}
        enforce_workspace(data, admin_in("default"))
        assert data["workspace"] == "default"

    def test_writer_same_workspace_specified_allowed(self):
        data = {"workspace": "default"}
        enforce_workspace(data, writer_in("default"))
        assert data["workspace"] == "default"

    def test_non_dict_passthrough(self):
        # Non-dict bodies are returned unchanged (e.g. streaming).
        result = enforce_workspace("not-a-dict", reader_in("default"))
        assert result == "not-a-dict"

    def test_with_capability_tightens_check(self):
        # Reader lacks graph:write; workspace-only check would pass
        # (scope is fine), but combined check must reject.
        data = {"workspace": "default"}
        with pytest.raises(web.HTTPForbidden):
            enforce_workspace(
                data, reader_in("default"), capability="graph:write",
            )

    def test_with_capability_passes_when_granted(self):
        data = {"workspace": "default"}
        enforce_workspace(
            data, reader_in("default"), capability="graph:read",
        )
        assert data["workspace"] == "default"


# -- helpers ---------------------------------------------------------------


class TestResponseHelpers:

    def test_auth_failure_is_401(self):
        exc = auth_failure()
        assert exc.status == 401
        assert "auth failure" in exc.text

    def test_access_denied_is_403(self):
        exc = access_denied()
        assert exc.status == 403
        assert "access denied" in exc.text


class TestSentinels:

    def test_public_and_authenticated_are_distinct(self):
        assert PUBLIC != AUTHENTICATED
        assert PUBLIC not in KNOWN_CAPABILITIES
        assert AUTHENTICATED not in KNOWN_CAPABILITIES
