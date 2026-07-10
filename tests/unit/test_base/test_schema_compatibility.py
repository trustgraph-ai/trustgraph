"""
Unit tests for schema_compatibility.is_strict_mode_compatible
"""

import pytest
from trustgraph.base.schema_compatibility import is_strict_mode_compatible


class TestIsStrictModeCompatible:

    def test_none_schema(self):
        assert is_strict_mode_compatible(None) is False

    def test_empty_dict(self):
        assert is_strict_mode_compatible({}) is True

    def test_simple_string(self):
        assert is_strict_mode_compatible({"type": "string"}) is True

    def test_compliant_object(self):
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
            },
            "required": ["name", "age"],
            "additionalProperties": False,
        }
        assert is_strict_mode_compatible(schema) is True

    def test_missing_additional_properties(self):
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        }
        assert is_strict_mode_compatible(schema) is False

    def test_additional_properties_true(self):
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
            "additionalProperties": True,
        }
        assert is_strict_mode_compatible(schema) is False

    def test_property_not_in_required(self):
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "nickname": {"type": "string"},
            },
            "required": ["name"],
            "additionalProperties": False,
        }
        assert is_strict_mode_compatible(schema) is False

    def test_open_ended_object_no_properties(self):
        schema = {
            "type": "object",
        }
        assert is_strict_mode_compatible(schema) is False

    def test_implicit_object_with_properties_key(self):
        schema = {
            "properties": {
                "x": {"type": "number"},
            },
            "required": ["x"],
            "additionalProperties": False,
        }
        assert is_strict_mode_compatible(schema) is True

    def test_nested_object_compliant(self):
        schema = {
            "type": "object",
            "properties": {
                "address": {
                    "type": "object",
                    "properties": {
                        "street": {"type": "string"},
                    },
                    "required": ["street"],
                    "additionalProperties": False,
                },
            },
            "required": ["address"],
            "additionalProperties": False,
        }
        assert is_strict_mode_compatible(schema) is True

    def test_nested_object_non_compliant(self):
        schema = {
            "type": "object",
            "properties": {
                "metadata": {
                    "type": "object",
                },
            },
            "required": ["metadata"],
            "additionalProperties": False,
        }
        assert is_strict_mode_compatible(schema) is False

    def test_array_with_compliant_items(self):
        schema = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                },
                "required": ["id"],
                "additionalProperties": False,
            },
        }
        assert is_strict_mode_compatible(schema) is True

    def test_array_with_non_compliant_items(self):
        schema = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"id": {"type": "integer"}},
            },
        }
        assert is_strict_mode_compatible(schema) is False

    def test_array_with_simple_items(self):
        schema = {
            "type": "array",
            "items": {"type": "string"},
        }
        assert is_strict_mode_compatible(schema) is True

    def test_oneof_all_compliant(self):
        schema = {
            "oneOf": [
                {"type": "string"},
                {"type": "integer"},
            ]
        }
        assert is_strict_mode_compatible(schema) is True

    def test_oneof_with_non_compliant_branch(self):
        schema = {
            "oneOf": [
                {"type": "string"},
                {"type": "object"},
            ]
        }
        assert is_strict_mode_compatible(schema) is False

    def test_anyof(self):
        schema = {
            "anyOf": [
                {"type": "string"},
                {"type": "number"},
            ]
        }
        assert is_strict_mode_compatible(schema) is True

    def test_allof(self):
        schema = {
            "allOf": [
                {
                    "type": "object",
                    "properties": {"a": {"type": "string"}},
                    "required": ["a"],
                    "additionalProperties": False,
                },
            ]
        }
        assert is_strict_mode_compatible(schema) is True

    def test_unsupported_minimum(self):
        schema = {"type": "integer", "minimum": 0}
        assert is_strict_mode_compatible(schema) is False

    def test_unsupported_maximum(self):
        schema = {"type": "integer", "maximum": 100}
        assert is_strict_mode_compatible(schema) is False

    def test_unsupported_pattern(self):
        schema = {"type": "string", "pattern": "^[a-z]+$"}
        assert is_strict_mode_compatible(schema) is False

    def test_unsupported_min_length(self):
        schema = {"type": "string", "minLength": 1}
        assert is_strict_mode_compatible(schema) is False

    def test_unsupported_max_length(self):
        schema = {"type": "string", "maxLength": 255}
        assert is_strict_mode_compatible(schema) is False

    def test_unsupported_min_items(self):
        schema = {"type": "array", "items": {"type": "string"}, "minItems": 1}
        assert is_strict_mode_compatible(schema) is False

    def test_unsupported_max_items(self):
        schema = {"type": "array", "items": {"type": "string"}, "maxItems": 10}
        assert is_strict_mode_compatible(schema) is False

    def test_unsupported_exclusive_minimum(self):
        schema = {"type": "number", "exclusiveMinimum": 0}
        assert is_strict_mode_compatible(schema) is False

    def test_unsupported_min_max_properties(self):
        schema = {
            "type": "object",
            "properties": {"a": {"type": "string"}},
            "required": ["a"],
            "additionalProperties": False,
            "minProperties": 1,
        }
        assert is_strict_mode_compatible(schema) is False

    def test_unsupported_constraint_inside_nested_property(self):
        schema = {
            "type": "object",
            "properties": {
                "score": {"type": "integer", "minimum": 0, "maximum": 100},
            },
            "required": ["score"],
            "additionalProperties": False,
        }
        assert is_strict_mode_compatible(schema) is False

    def test_nullable_property(self):
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": ["string", "null"]},
            },
            "required": ["name"],
            "additionalProperties": False,
        }
        assert is_strict_mode_compatible(schema) is True

    def test_realistic_compliant_schema(self):
        schema = {
            "type": "object",
            "properties": {
                "action": {"type": "string"},
                "services": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": ["action", "services"],
            "additionalProperties": False,
        }
        assert is_strict_mode_compatible(schema) is True

    def test_realistic_non_compliant_optional_field(self):
        schema = {
            "type": "object",
            "properties": {
                "action": {"type": "string"},
                "reason": {"type": "string"},
            },
            "required": ["action"],
            "additionalProperties": False,
        }
        assert is_strict_mode_compatible(schema) is False
