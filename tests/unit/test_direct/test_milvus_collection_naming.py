"""
Unit tests for Milvus collection name sanitization functionality
"""

import pytest
from trustgraph.direct.milvus_doc_embeddings import make_safe_collection_name


class TestMilvusCollectionNaming:
    """Test cases for Milvus collection name generation and sanitization"""

    def test_make_safe_collection_name_basic(self):
        """Test basic collection name creation"""
        result = make_safe_collection_name(
            user="test_user",
            collection="test_collection",
            prefix="doc"
        )
        assert result == "doc_test_user_test_collection"

    def test_make_safe_collection_name_with_special_characters(self):
        """Test collection name creation with special characters that need sanitization"""
        result = make_safe_collection_name(
            user="user@domain.com",
            collection="test-collection.v2",
            prefix="entity"
        )
        assert result == "entity_user_domain_com_test_collection_v2"

    def test_make_safe_collection_name_with_unicode(self):
        """Test collection name creation with Unicode characters"""
        result = make_safe_collection_name(
            user="测试用户",
            collection="colección_española",
            prefix="doc"
        )
        assert result == "doc_default_colecci_n_espa_ola"

    def test_make_safe_collection_name_with_spaces(self):
        """Test collection name creation with spaces"""
        result = make_safe_collection_name(
            user="test user",
            collection="my test collection",
            prefix="entity"
        )
        assert result == "entity_test_user_my_test_collection"

    def test_make_safe_collection_name_with_multiple_consecutive_special_chars(self):
        """Test collection name creation with multiple consecutive special characters"""
        result = make_safe_collection_name(
            user="user@@@domain!!!",
            collection="test---collection...v2",
            prefix="doc"
        )
        assert result == "doc_user_domain_test_collection_v2"

    def test_make_safe_collection_name_with_leading_trailing_underscores(self):
        """Test collection name creation with leading/trailing special characters"""
        result = make_safe_collection_name(
            user="__test_user__",
            collection="@@test_collection##",
            prefix="entity"
        )
        assert result == "entity_test_user_test_collection"

    def test_make_safe_collection_name_empty_user(self):
        """Test collection name creation with empty user (should fallback to 'default')"""
        result = make_safe_collection_name(
            user="",
            collection="test_collection",
            prefix="doc"
        )
        assert result == "doc_default_test_collection"

    def test_make_safe_collection_name_empty_collection(self):
        """Test collection name creation with empty collection (should fallback to 'default')"""
        result = make_safe_collection_name(
            user="test_user",
            collection="",
            prefix="doc"
        )
        assert result == "doc_test_user_default"

    def test_make_safe_collection_name_both_empty(self):
        """Test collection name creation with both user and collection empty"""
        result = make_safe_collection_name(
            user="",
            collection="",
            prefix="doc"
        )
        assert result == "doc_default_default"

    def test_make_safe_collection_name_only_special_characters(self):
        """Test collection name creation with only special characters (should fallback to 'default')"""
        result = make_safe_collection_name(
            user="@@@!!!",
            collection="---###",
            prefix="entity"
        )
        assert result == "entity_default_default"

    def test_make_safe_collection_name_whitespace_only(self):
        """Test collection name creation with whitespace-only strings"""
        result = make_safe_collection_name(
            user="   \n\t   ",
            collection="  \r\n  ",
            prefix="doc"
        )
        assert result == "doc_default_default"

    def test_make_safe_collection_name_mixed_valid_invalid_chars(self):
        """Test collection name creation with mixed valid and invalid characters"""
        result = make_safe_collection_name(
            user="user123@test",
            collection="coll_2023.v1",
            prefix="entity"
        )
        assert result == "entity_user123_test_coll_2023_v1"

    def test_make_safe_collection_name_different_prefixes(self):
        """Test collection name creation with different prefixes"""
        user = "test_user"
        collection = "test_collection"

        doc_result = make_safe_collection_name(user, collection, "doc")
        entity_result = make_safe_collection_name(user, collection, "entity")
        custom_result = make_safe_collection_name(user, collection, "custom")

        assert doc_result == "doc_test_user_test_collection"
        assert entity_result == "entity_test_user_test_collection"
        assert custom_result == "custom_test_user_test_collection"

    def test_make_safe_collection_name_different_dimensions(self):
        """Test collection name creation - dimension handling no longer part of function"""
        user = "test_user"
        collection = "test_collection"
        prefix = "doc"

        # With new API, dimensions are handled separately, function always returns same result
        result = make_safe_collection_name(user, collection, prefix)

        assert result == "doc_test_user_test_collection"

    def test_make_safe_collection_name_long_names(self):
        """Test collection name creation with very long user/collection names"""
        long_user = "a" * 100
        long_collection = "b" * 100

        result = make_safe_collection_name(
            user=long_user,
            collection=long_collection,
            prefix="doc"
        )

        expected = f"doc_{long_user}_{long_collection}"
        assert result == expected
        assert len(result) > 200  # Verify it handles long names

    def test_make_safe_collection_name_numeric_values(self):
        """Test collection name creation with numeric user/collection values"""
        result = make_safe_collection_name(
            user="user123",
            collection="collection456",
            prefix="doc"
        )
        assert result == "doc_user123_collection456"

    def test_make_safe_collection_name_case_sensitivity(self):
        """Test that collection name creation preserves case"""
        result = make_safe_collection_name(
            user="TestUser",
            collection="TestCollection",
            prefix="Doc"
        )
        assert result == "Doc_TestUser_TestCollection"

    def test_make_safe_collection_name_realistic_examples(self):
        """Test collection name creation with realistic user/collection combinations"""
        test_cases = [
            # (user, collection, expected_safe_user, expected_safe_collection)
            ("john.doe", "production-2024", "john_doe", "production_2024"),
            ("team@company.com", "ml_models.v1", "team_company_com", "ml_models_v1"),
            ("user_123", "test_collection", "user_123", "test_collection"),
            ("αβγ-user", "测试集合", "user", "default"),
        ]

        for user, collection, expected_user, expected_collection in test_cases:
            result = make_safe_collection_name(user, collection, "doc")
            assert result == f"doc_{expected_user}_{expected_collection}"

    def test_make_safe_collection_name_matches_qdrant_pattern(self):
        """Test that Milvus collection names follow similar pattern to Qdrant (but without dimension in name)"""
        # Qdrant uses: "d_{user}_{collection}_{dimension}" and "t_{user}_{collection}_{dimension}"
        # New Milvus API uses: "{prefix}_{safe_user}_{safe_collection}" (dimension handled separately)

        user = "test.user@domain.com"
        collection = "test-collection.v2"

        doc_result = make_safe_collection_name(user, collection, "doc")
        entity_result = make_safe_collection_name(user, collection, "entity")

        # Should follow the pattern but with sanitized names and no dimension
        assert doc_result == "doc_test_user_domain_com_test_collection_v2"
        assert entity_result == "entity_test_user_domain_com_test_collection_v2"

        # Verify structure matches expected pattern
        assert doc_result.startswith("doc_")
        assert entity_result.startswith("entity_")
        # Dimension is no longer part of the collection name