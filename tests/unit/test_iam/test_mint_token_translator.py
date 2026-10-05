"""
Tests for user_context_json round-trip through the IamRequest translator.
"""

import json

from trustgraph.messaging.translators.iam import (
    IamRequestTranslator,
)


USER_CONTEXT = {
    "user_id": "alice",
    "roles": ["analyst"],
    "purpose": "review",
}


class TestIamRequestTranslatorUserContext:

    def test_decode_includes_user_context_json(self):
        t = IamRequestTranslator()
        data = {
            "operation": "mint-token",
            "user_id": "alice",
            "workspace": "default",
            "user_context_json": json.dumps(USER_CONTEXT),
        }
        req = t.decode(data)
        assert req.operation == "mint-token"
        assert req.user_id == "alice"
        assert req.workspace == "default"
        assert json.loads(req.user_context_json) == USER_CONTEXT

    def test_decode_missing_user_context_json_defaults_empty(self):
        t = IamRequestTranslator()
        data = {"operation": "login", "username": "bob"}
        req = t.decode(data)
        assert req.user_context_json == ""

    def test_encode_includes_user_context_json(self):
        t = IamRequestTranslator()
        data = {
            "operation": "mint-token",
            "user_id": "alice",
            "workspace": "default",
            "user_context_json": json.dumps(USER_CONTEXT),
        }
        req = t.decode(data)
        encoded = t.encode(req)
        assert encoded["user_context_json"] == json.dumps(USER_CONTEXT)

    def test_encode_omits_empty_user_context_json(self):
        t = IamRequestTranslator()
        data = {"operation": "login", "username": "bob"}
        req = t.decode(data)
        encoded = t.encode(req)
        assert "user_context_json" not in encoded

    def test_round_trip(self):
        t = IamRequestTranslator()
        data = {
            "operation": "mint-token",
            "user_id": "alice",
            "workspace": "default",
            "user_context_json": json.dumps(USER_CONTEXT),
        }
        req = t.decode(data)
        encoded = t.encode(req)
        req2 = t.decode(encoded)
        assert req2.operation == req.operation
        assert req2.user_id == req.user_id
        assert req2.workspace == req.workspace
        assert req2.user_context_json == req.user_context_json
