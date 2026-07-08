"""
Unit tests for entity URI normalization.

Covers ASCII behaviour and, critically, non-ASCII (e.g. Chinese) entity
names and types, which must be preserved rather than stripped so that
distinct entities do not collapse onto a single URI.
"""

import pytest
from trustgraph.extract.kg.ontology.entity_normalizer import (
    normalize_entity_name,
    normalize_type_identifier,
    build_entity_uri,
    EntityRegistry,
)


class TestNormalizeEntityNameAscii:
    """ASCII normalization must keep working as before."""

    def test_lowercases_and_hyphenates(self):
        assert normalize_entity_name("Cornish pasty") == "cornish-pasty"

    def test_strips_punctuation(self):
        assert normalize_entity_name("beef!!!") == "beef"

    def test_collapses_and_trims_hyphens(self):
        assert normalize_entity_name("  beef   stew  ") == "beef-stew"


class TestNormalizeEntityNameUnicode:
    """Non-ASCII names must be preserved, not stripped to empty."""

    def test_chinese_name_preserved(self):
        # Previously the ASCII-only filter deleted every CJK character,
        # collapsing the name to "".
        assert normalize_entity_name("苹果") == "苹果"

    def test_chinese_name_with_space(self):
        assert normalize_entity_name("有机 苹果") == "有机-苹果"

    def test_distinct_chinese_names_stay_distinct(self):
        assert normalize_entity_name("苹果") != normalize_entity_name("香蕉")

    def test_mixed_ascii_and_chinese(self):
        assert normalize_entity_name("iPhone 手机") == "iphone-手机"


class TestNormalizeTypeIdentifierUnicode:
    def test_ascii_prefixed_type(self):
        assert normalize_type_identifier("fo/Recipe") == "fo-recipe"

    def test_chinese_type_preserved(self):
        assert normalize_type_identifier("食物") == "食物"


class TestBuildEntityUriUnicode:
    def test_distinct_chinese_entities_get_distinct_uris(self):
        # This is the core regression: with ASCII-only normalization both
        # names collapsed to the same URI, merging unrelated entities.
        uri_apple = build_entity_uri("苹果", "水果", "food")
        uri_banana = build_entity_uri("香蕉", "水果", "food")
        assert uri_apple != uri_banana
        assert uri_apple.endswith("苹果")
        assert uri_banana.endswith("香蕉")

    def test_uri_is_not_bare_prefix(self):
        uri = build_entity_uri("苹果", "水果", "food")
        # Must not collapse to ".../food/水果-" or ".../food/-"
        assert not uri.endswith("-")


class TestEntityRegistryUnicode:
    def test_distinct_chinese_entities_not_deduplicated(self):
        registry = EntityRegistry("food")
        uri_apple = registry.get_or_create_uri("苹果", "水果")
        uri_banana = registry.get_or_create_uri("香蕉", "水果")
        assert uri_apple != uri_banana
        assert registry.size() == 2
