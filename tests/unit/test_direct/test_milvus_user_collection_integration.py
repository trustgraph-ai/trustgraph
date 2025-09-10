"""
Integration tests for Milvus user/collection functionality
Tests the complete flow of the new user/collection parameter handling
"""

import pytest
from unittest.mock import MagicMock, patch

from trustgraph.direct.milvus_doc_embeddings import DocVectors, make_safe_collection_name
from trustgraph.direct.milvus_graph_embeddings import EntityVectors


class TestMilvusUserCollectionIntegration:
    """Test cases for Milvus user/collection integration functionality"""

    @patch('trustgraph.direct.milvus_doc_embeddings.MilvusClient')
    def test_doc_vectors_collection_creation_with_user_collection(self, mock_milvus_client):
        """Test DocVectors creates collections with proper user/collection names"""
        mock_client = MagicMock()
        mock_milvus_client.return_value = mock_client
        
        doc_vectors = DocVectors(uri="http://test:19530", prefix="doc")
        
        # Test collection creation for different user/collection combinations
        test_cases = [
            ("user1", "collection1", [0.1, 0.2, 0.3]),
            ("user2", "collection2", [0.1, 0.2, 0.3, 0.4]),
            ("user@domain.com", "test-collection.v1", [0.1, 0.2, 0.3]),
        ]
        
        for user, collection, vector in test_cases:
            doc_vectors.insert(vector, "test document", user, collection)
            
            expected_collection_name = make_safe_collection_name(
                user, collection, len(vector), "doc"
            )
            
            # Verify collection was created with correct name
            assert (len(vector), user, collection) in doc_vectors.collections
            assert doc_vectors.collections[(len(vector), user, collection)] == expected_collection_name

    @patch('trustgraph.direct.milvus_graph_embeddings.MilvusClient')
    def test_entity_vectors_collection_creation_with_user_collection(self, mock_milvus_client):
        """Test EntityVectors creates collections with proper user/collection names"""
        mock_client = MagicMock()
        mock_milvus_client.return_value = mock_client
        
        entity_vectors = EntityVectors(uri="http://test:19530", prefix="entity")
        
        # Test collection creation for different user/collection combinations
        test_cases = [
            ("user1", "collection1", [0.1, 0.2, 0.3]),
            ("user2", "collection2", [0.1, 0.2, 0.3, 0.4]),
            ("user@domain.com", "test-collection.v1", [0.1, 0.2, 0.3]),
        ]
        
        for user, collection, vector in test_cases:
            entity_vectors.insert(vector, "test entity", user, collection)
            
            expected_collection_name = make_safe_collection_name(
                user, collection, len(vector), "entity"
            )
            
            # Verify collection was created with correct name
            assert (len(vector), user, collection) in entity_vectors.collections
            assert entity_vectors.collections[(len(vector), user, collection)] == expected_collection_name

    @patch('trustgraph.direct.milvus_doc_embeddings.MilvusClient')
    def test_doc_vectors_search_uses_correct_collection(self, mock_milvus_client):
        """Test DocVectors search uses the correct collection for user/collection"""
        mock_client = MagicMock()
        mock_milvus_client.return_value = mock_client
        
        # Mock search results
        mock_client.search.return_value = [
            {"entity": {"doc": "test document"}}
        ]
        
        doc_vectors = DocVectors(uri="http://test:19530", prefix="doc")
        
        # First insert to create collection
        vector = [0.1, 0.2, 0.3]
        user = "test_user"
        collection = "test_collection"
        
        doc_vectors.insert(vector, "test doc", user, collection)
        
        # Now search
        result = doc_vectors.search(vector, user, collection, limit=5)
        
        # Verify search was called with correct collection name
        expected_collection_name = make_safe_collection_name(user, collection, 3, "doc")
        mock_client.search.assert_called_once()
        search_call = mock_client.search.call_args
        assert search_call[1]["collection_name"] == expected_collection_name

    @patch('trustgraph.direct.milvus_graph_embeddings.MilvusClient')  
    def test_entity_vectors_search_uses_correct_collection(self, mock_milvus_client):
        """Test EntityVectors search uses the correct collection for user/collection"""
        mock_client = MagicMock()
        mock_milvus_client.return_value = mock_client
        
        # Mock search results
        mock_client.search.return_value = [
            {"entity": {"entity": "test entity"}}
        ]
        
        entity_vectors = EntityVectors(uri="http://test:19530", prefix="entity")
        
        # First insert to create collection
        vector = [0.1, 0.2, 0.3]
        user = "test_user"
        collection = "test_collection"
        
        entity_vectors.insert(vector, "test entity", user, collection)
        
        # Now search
        result = entity_vectors.search(vector, user, collection, limit=5)
        
        # Verify search was called with correct collection name
        expected_collection_name = make_safe_collection_name(user, collection, 3, "entity")
        mock_client.search.assert_called_once()
        search_call = mock_client.search.call_args
        assert search_call[1]["collection_name"] == expected_collection_name

    @patch('trustgraph.direct.milvus_doc_embeddings.MilvusClient')
    def test_doc_vectors_collection_isolation(self, mock_milvus_client):
        """Test that different user/collection combinations create separate collections"""
        mock_client = MagicMock()
        mock_milvus_client.return_value = mock_client
        
        doc_vectors = DocVectors(uri="http://test:19530", prefix="doc")
        
        # Insert same vector for different user/collection combinations
        vector = [0.1, 0.2, 0.3]
        doc_vectors.insert(vector, "user1 doc", "user1", "collection1")
        doc_vectors.insert(vector, "user2 doc", "user2", "collection2") 
        doc_vectors.insert(vector, "user1 doc2", "user1", "collection2")
        
        # Verify three separate collections were created
        assert len(doc_vectors.collections) == 3
        
        collection_names = set(doc_vectors.collections.values())
        expected_names = {
            "doc_user1_collection1_3",
            "doc_user2_collection2_3", 
            "doc_user1_collection2_3"
        }
        assert collection_names == expected_names

    @patch('trustgraph.direct.milvus_graph_embeddings.MilvusClient')
    def test_entity_vectors_collection_isolation(self, mock_milvus_client):
        """Test that different user/collection combinations create separate collections"""
        mock_client = MagicMock()
        mock_milvus_client.return_value = mock_client
        
        entity_vectors = EntityVectors(uri="http://test:19530", prefix="entity")
        
        # Insert same vector for different user/collection combinations
        vector = [0.1, 0.2, 0.3]
        entity_vectors.insert(vector, "user1 entity", "user1", "collection1")
        entity_vectors.insert(vector, "user2 entity", "user2", "collection2")
        entity_vectors.insert(vector, "user1 entity2", "user1", "collection2")
        
        # Verify three separate collections were created
        assert len(entity_vectors.collections) == 3
        
        collection_names = set(entity_vectors.collections.values())
        expected_names = {
            "entity_user1_collection1_3",
            "entity_user2_collection2_3",
            "entity_user1_collection2_3"
        }
        assert collection_names == expected_names

    @patch('trustgraph.direct.milvus_doc_embeddings.MilvusClient')
    def test_doc_vectors_dimension_isolation(self, mock_milvus_client):
        """Test that different dimensions create separate collections even with same user/collection"""
        mock_client = MagicMock()
        mock_milvus_client.return_value = mock_client
        
        doc_vectors = DocVectors(uri="http://test:19530", prefix="doc")
        
        user = "test_user"
        collection = "test_collection"
        
        # Insert vectors with different dimensions
        doc_vectors.insert([0.1, 0.2, 0.3], "3D doc", user, collection)           # 3D
        doc_vectors.insert([0.1, 0.2, 0.3, 0.4], "4D doc", user, collection)     # 4D
        doc_vectors.insert([0.1, 0.2], "2D doc", user, collection)               # 2D
        
        # Verify three separate collections were created for different dimensions
        assert len(doc_vectors.collections) == 3
        
        collection_names = set(doc_vectors.collections.values())
        expected_names = {
            "doc_test_user_test_collection_3",  # 3D
            "doc_test_user_test_collection_4",  # 4D
            "doc_test_user_test_collection_2"   # 2D
        }
        assert collection_names == expected_names

    @patch('trustgraph.direct.milvus_doc_embeddings.MilvusClient')
    def test_doc_vectors_collection_reuse(self, mock_milvus_client):
        """Test that same user/collection/dimension reuses existing collection"""
        mock_client = MagicMock()
        mock_milvus_client.return_value = mock_client
        
        doc_vectors = DocVectors(uri="http://test:19530", prefix="doc")
        
        user = "test_user"
        collection = "test_collection"
        vector = [0.1, 0.2, 0.3]
        
        # Insert multiple documents with same user/collection/dimension
        doc_vectors.insert(vector, "doc1", user, collection)
        doc_vectors.insert(vector, "doc2", user, collection)
        doc_vectors.insert(vector, "doc3", user, collection)
        
        # Verify only one collection was created
        assert len(doc_vectors.collections) == 1
        
        expected_collection_name = "doc_test_user_test_collection_3"
        assert doc_vectors.collections[(3, user, collection)] == expected_collection_name

    @patch('trustgraph.direct.milvus_doc_embeddings.MilvusClient')
    def test_doc_vectors_special_characters_handling(self, mock_milvus_client):
        """Test that special characters in user/collection names are handled correctly"""
        mock_client = MagicMock()
        mock_milvus_client.return_value = mock_client
        
        doc_vectors = DocVectors(uri="http://test:19530", prefix="doc")
        
        # Test various special character combinations
        test_cases = [
            ("user@domain.com", "test-collection.v1", "doc_user_domain_com_test_collection_v1_3"),
            ("user_123", "collection_456", "doc_user_123_collection_456_3"),  
            ("user with spaces", "collection with spaces", "doc_user_with_spaces_collection_with_spaces_3"),
            ("user@@@test", "collection---test", "doc_user_test_collection_test_3"),
        ]
        
        vector = [0.1, 0.2, 0.3]
        
        for user, collection, expected_name in test_cases:
            doc_vectors_instance = DocVectors(uri="http://test:19530", prefix="doc")
            doc_vectors_instance.insert(vector, "test doc", user, collection)
            
            assert doc_vectors_instance.collections[(3, user, collection)] == expected_name

    def test_collection_name_backward_compatibility(self):
        """Test that new collection names don't conflict with old pattern"""
        # Old pattern was: {prefix}_{dimension}
        # New pattern is: {prefix}_{safe_user}_{safe_collection}_{dimension}
        
        # The new pattern should never generate names that match the old pattern
        old_pattern_examples = ["doc_384", "entity_768", "doc_512"]
        
        test_cases = [
            ("user", "collection", 384, "doc"),
            ("test", "test", 768, "entity"), 
            ("a", "b", 512, "doc"),
        ]
        
        for user, collection, dimension, prefix in test_cases:
            new_name = make_safe_collection_name(user, collection, dimension, prefix)
            
            # New names should have at least 4 underscores (prefix_user_collection_dimension)
            # Old names had only 1 underscore (prefix_dimension)
            assert new_name.count('_') >= 3, f"New name {new_name} doesn't have enough underscores"
            
            # New names should not match old pattern
            assert new_name not in old_pattern_examples, f"New name {new_name} conflicts with old pattern"

    def test_user_collection_isolation_regression(self):
        """
        Regression test to ensure user/collection parameters prevent data mixing.
        
        This test guards against the bug where all users shared the same Milvus
        collections, causing data contamination between users/collections.
        """
        
        # Test the specific case that was broken before the fix
        user1, collection1 = "my_user", "test_coll_1" 
        user2, collection2 = "other_user", "production_data"
        
        dimension = 384
        
        # Generate collection names
        doc_name1 = make_safe_collection_name(user1, collection1, dimension, "doc")
        doc_name2 = make_safe_collection_name(user2, collection2, dimension, "doc")
        
        entity_name1 = make_safe_collection_name(user1, collection1, dimension, "entity")
        entity_name2 = make_safe_collection_name(user2, collection2, dimension, "entity")
        
        # Verify complete isolation
        assert doc_name1 != doc_name2, "Document collections should be isolated"
        assert entity_name1 != entity_name2, "Entity collections should be isolated"
        
        # Verify names match expected pattern from Qdrant
        # Qdrant uses: d_{user}_{collection}_{dimension}, t_{user}_{collection}_{dimension}
        # Milvus uses: doc_{safe_user}_{safe_collection}_{dimension}, entity_{safe_user}_{safe_collection}_{dimension}
        assert doc_name1 == "doc_my_user_test_coll_1_384"
        assert doc_name2 == "doc_other_user_production_data_384"
        assert entity_name1 == "entity_my_user_test_coll_1_384"
        assert entity_name2 == "entity_other_user_production_data_384"
        
        # This test would have FAILED with the old implementation that used:
        # - doc_384 for all document embeddings (no user/collection differentiation)
        # - entity_384 for all graph embeddings (no user/collection differentiation)