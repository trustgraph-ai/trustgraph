"""
Tests for Neo4j user/collection isolation in triples storage and query
"""

import pytest
from unittest.mock import MagicMock, patch, call

from trustgraph.storage.triples.neo4j.write import Processor as StorageProcessor
from trustgraph.query.triples.neo4j.service import Processor as QueryProcessor
from trustgraph.schema import Triples, Triple, Value, Metadata
from trustgraph.schema import TriplesQueryRequest


class TestNeo4jUserCollectionIsolation:
    """Test cases for Neo4j user/collection isolation functionality"""

    @patch('trustgraph.storage.triples.neo4j.write.GraphDatabase')
    def test_storage_creates_indexes_with_user_collection(self, mock_graph_db):
        """Test that storage service creates compound indexes for user/collection"""
        taskgroup_mock = MagicMock()
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        
        processor = StorageProcessor(taskgroup=taskgroup_mock)
        
        # Verify both legacy and new compound indexes are created
        expected_indexes = [
            "CREATE INDEX Node_uri FOR (n:Node) ON (n.uri)",
            "CREATE INDEX Literal_value FOR (n:Literal) ON (n.value)",
            "CREATE INDEX Rel_uri FOR ()-[r:Rel]-() ON (r.uri)",
            "CREATE INDEX node_user_collection_uri FOR (n:Node) ON (n.user, n.collection, n.uri)",
            "CREATE INDEX literal_user_collection_value FOR (n:Literal) ON (n.user, n.collection, n.value)",
            "CREATE INDEX rel_user FOR ()-[r:Rel]-() ON (r.user)",
            "CREATE INDEX rel_collection FOR ()-[r:Rel]-() ON (r.collection)"
        ]
        
        # Check that all expected indexes were created
        for expected_query in expected_indexes:
            mock_session.run.assert_any_call(expected_query)

    @patch('trustgraph.storage.triples.neo4j.write.GraphDatabase')
    @pytest.mark.asyncio
    async def test_store_triples_with_user_collection(self, mock_graph_db):
        """Test that triples are stored with user/collection properties"""
        taskgroup_mock = MagicMock()
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        
        processor = StorageProcessor(taskgroup=taskgroup_mock)
        
        # Create test message with user/collection metadata
        metadata = Metadata(
            id="test-id",
            user="test_user",
            collection="test_collection"
        )
        
        triple = Triple(
            s=Value(value="http://example.com/subject", is_uri=True),
            p=Value(value="http://example.com/predicate", is_uri=True),
            o=Value(value="literal_value", is_uri=False)
        )
        
        message = Triples(
            metadata=metadata,
            triples=[triple]
        )
        
        # Mock execute_query to return summaries
        mock_summary = MagicMock()
        mock_summary.counters.nodes_created = 1
        mock_summary.result_available_after = 10
        mock_driver.execute_query.return_value.summary = mock_summary
        
        await processor.store_triples(message)
        
        # Verify nodes and relationships were created with user/collection properties
        expected_calls = [
            call(
                "MERGE (n:Node {uri: $uri, user: $user, collection: $collection})",
                uri="http://example.com/subject",
                user="test_user",
                collection="test_collection",
                database_='neo4j'
            ),
            call(
                "MERGE (n:Literal {value: $value, user: $user, collection: $collection})",
                value="literal_value",
                user="test_user",
                collection="test_collection",
                database_='neo4j'
            ),
            call(
                "MATCH (src:Node {uri: $src, user: $user, collection: $collection}) "
                "MATCH (dest:Literal {value: $dest, user: $user, collection: $collection}) "
                "MERGE (src)-[:Rel {uri: $uri, user: $user, collection: $collection}]->(dest)",
                src="http://example.com/subject",
                dest="literal_value",
                uri="http://example.com/predicate",
                user="test_user",
                collection="test_collection",
                database_='neo4j'
            )
        ]
        
        for expected_call in expected_calls:
            mock_driver.execute_query.assert_any_call(*expected_call.args, **expected_call.kwargs)

    @patch('trustgraph.storage.triples.neo4j.write.GraphDatabase')
    @pytest.mark.asyncio
    async def test_store_triples_with_default_user_collection(self, mock_graph_db):
        """Test that default user/collection are used when not provided"""
        taskgroup_mock = MagicMock()
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        
        processor = StorageProcessor(taskgroup=taskgroup_mock)
        
        # Create test message without user/collection
        metadata = Metadata(id="test-id")
        
        triple = Triple(
            s=Value(value="http://example.com/subject", is_uri=True),
            p=Value(value="http://example.com/predicate", is_uri=True),
            o=Value(value="http://example.com/object", is_uri=True)
        )
        
        message = Triples(
            metadata=metadata,
            triples=[triple]
        )
        
        # Mock execute_query
        mock_summary = MagicMock()
        mock_summary.counters.nodes_created = 1
        mock_summary.result_available_after = 10
        mock_driver.execute_query.return_value.summary = mock_summary
        
        await processor.store_triples(message)
        
        # Verify defaults were used
        mock_driver.execute_query.assert_any_call(
            "MERGE (n:Node {uri: $uri, user: $user, collection: $collection})",
            uri="http://example.com/subject",
            user="default",
            collection="default",
            database_='neo4j'
        )

    @patch('trustgraph.query.triples.neo4j.service.GraphDatabase')
    @pytest.mark.asyncio
    async def test_query_triples_filters_by_user_collection(self, mock_graph_db):
        """Test that query service filters results by user/collection"""
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        
        processor = QueryProcessor(taskgroup=MagicMock())
        
        # Create test query
        query = TriplesQueryRequest(
            user="test_user",
            collection="test_collection",
            s=Value(value="http://example.com/subject", is_uri=True),
            p=Value(value="http://example.com/predicate", is_uri=True),
            o=None
        )
        
        # Mock query results
        mock_records = [
            MagicMock(data=lambda: {"dest": "http://example.com/object1"}),
            MagicMock(data=lambda: {"dest": "literal_value"})
        ]
        
        mock_driver.execute_query.return_value = (mock_records, MagicMock(), MagicMock())
        
        result = await processor.query_triples(query)
        
        # Verify queries include user/collection filters
        expected_literal_query = (
            "MATCH (src:Node {uri: $src, user: $user, collection: $collection})-"
            "[rel:Rel {uri: $rel, user: $user, collection: $collection}]->"
            "(dest:Literal {user: $user, collection: $collection}) "
            "RETURN dest.value as dest"
        )
        
        expected_node_query = (
            "MATCH (src:Node {uri: $src, user: $user, collection: $collection})-"
            "[rel:Rel {uri: $rel, user: $user, collection: $collection}]->"
            "(dest:Node {user: $user, collection: $collection}) "
            "RETURN dest.uri as dest"
        )
        
        # Check that queries were executed with user/collection parameters
        calls = mock_driver.execute_query.call_args_list
        assert any(
            expected_literal_query in str(call) and 
            "user='test_user'" in str(call) and 
            "collection='test_collection'" in str(call)
            for call in calls
        )

    @patch('trustgraph.query.triples.neo4j.service.GraphDatabase')
    @pytest.mark.asyncio
    async def test_query_triples_with_default_user_collection(self, mock_graph_db):
        """Test that query service uses defaults when user/collection not provided"""
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        
        processor = QueryProcessor(taskgroup=MagicMock())
        
        # Create test query without user/collection
        query = TriplesQueryRequest(
            s=None,
            p=None,
            o=None
        )
        
        # Mock empty results
        mock_driver.execute_query.return_value = ([], MagicMock(), MagicMock())
        
        result = await processor.query_triples(query)
        
        # Verify defaults were used in queries
        calls = mock_driver.execute_query.call_args_list
        assert any(
            "user='default'" in str(call) and "collection='default'" in str(call)
            for call in calls
        )

    @patch('trustgraph.storage.triples.neo4j.write.GraphDatabase')
    @pytest.mark.asyncio
    async def test_data_isolation_between_users(self, mock_graph_db):
        """Test that data from different users is properly isolated"""
        taskgroup_mock = MagicMock()
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        
        processor = StorageProcessor(taskgroup=taskgroup_mock)
        
        # Create messages for different users
        message_user1 = Triples(
            metadata=Metadata(user="user1", collection="coll1"),
            triples=[
                Triple(
                    s=Value(value="http://example.com/user1/subject", is_uri=True),
                    p=Value(value="http://example.com/predicate", is_uri=True),
                    o=Value(value="user1_data", is_uri=False)
                )
            ]
        )
        
        message_user2 = Triples(
            metadata=Metadata(user="user2", collection="coll2"),
            triples=[
                Triple(
                    s=Value(value="http://example.com/user2/subject", is_uri=True),
                    p=Value(value="http://example.com/predicate", is_uri=True),
                    o=Value(value="user2_data", is_uri=False)
                )
            ]
        )
        
        # Mock execute_query
        mock_summary = MagicMock()
        mock_summary.counters.nodes_created = 1
        mock_summary.result_available_after = 10
        mock_driver.execute_query.return_value.summary = mock_summary
        
        # Store data for both users
        await processor.store_triples(message_user1)
        await processor.store_triples(message_user2)
        
        # Verify user1 data was stored with user1/coll1
        mock_driver.execute_query.assert_any_call(
            "MERGE (n:Literal {value: $value, user: $user, collection: $collection})",
            value="user1_data",
            user="user1",
            collection="coll1",
            database_='neo4j'
        )
        
        # Verify user2 data was stored with user2/coll2
        mock_driver.execute_query.assert_any_call(
            "MERGE (n:Literal {value: $value, user: $user, collection: $collection})",
            value="user2_data",
            user="user2",
            collection="coll2",
            database_='neo4j'
        )

    @patch('trustgraph.query.triples.neo4j.service.GraphDatabase')
    @pytest.mark.asyncio
    async def test_wildcard_query_respects_user_collection(self, mock_graph_db):
        """Test that wildcard queries still filter by user/collection"""
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        
        processor = QueryProcessor(taskgroup=MagicMock())
        
        # Create wildcard query (all nulls) with user/collection
        query = TriplesQueryRequest(
            user="test_user",
            collection="test_collection",
            s=None,
            p=None,
            o=None
        )
        
        # Mock results
        mock_driver.execute_query.return_value = ([], MagicMock(), MagicMock())
        
        result = await processor.query_triples(query)
        
        # Verify wildcard queries include user/collection filters
        wildcard_query = (
            "MATCH (src:Node {user: $user, collection: $collection})-"
            "[rel:Rel {user: $user, collection: $collection}]->"
            "(dest:Literal {user: $user, collection: $collection}) "
            "RETURN src.uri as src, rel.uri as rel, dest.value as dest"
        )
        
        calls = mock_driver.execute_query.call_args_list
        assert any(
            wildcard_query in str(call) and
            "user='test_user'" in str(call) and
            "collection='test_collection'" in str(call)
            for call in calls
        )

    def test_add_args_includes_neo4j_parameters(self):
        """Test that add_args includes Neo4j-specific parameters"""
        from argparse import ArgumentParser
        from unittest.mock import patch
        
        parser = ArgumentParser()
        
        with patch('trustgraph.storage.triples.neo4j.write.TriplesStoreService.add_args'):
            StorageProcessor.add_args(parser)
        
        args = parser.parse_args([])
        
        assert hasattr(args, 'graph_host')
        assert hasattr(args, 'username')
        assert hasattr(args, 'password')
        assert hasattr(args, 'database')
        
        # Check defaults
        assert args.graph_host == 'bolt://neo4j:7687'
        assert args.username == 'neo4j'
        assert args.password == 'password'
        assert args.database == 'neo4j'


class TestNeo4jUserCollectionRegression:
    """Regression tests to ensure user/collection isolation prevents data leaks"""
    
    @patch('trustgraph.query.triples.neo4j.service.GraphDatabase')
    @pytest.mark.asyncio  
    async def test_regression_no_cross_user_data_access(self, mock_graph_db):
        """
        Regression test: Ensure user1 cannot access user2's data
        
        This test guards against the bug where all users shared the same
        Neo4j graph space, causing data contamination between users.
        """
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        
        processor = QueryProcessor(taskgroup=MagicMock())
        
        # User1 queries for all triples
        query_user1 = TriplesQueryRequest(
            user="user1",
            collection="collection1",
            s=None, p=None, o=None
        )
        
        # Mock that the database has data but none matching user1/collection1
        mock_driver.execute_query.return_value = ([], MagicMock(), MagicMock())
        
        result = await processor.query_triples(query_user1)
        
        # Verify empty results (user1 cannot see other users' data)
        assert len(result) == 0
        
        # Verify the query included user/collection filters
        calls = mock_driver.execute_query.call_args_list
        for call in calls:
            query_str = str(call)
            if "MATCH" in query_str:
                assert "user: $user" in query_str or "user='user1'" in query_str
                assert "collection: $collection" in query_str or "collection='collection1'" in query_str
    
    @patch('trustgraph.storage.triples.neo4j.write.GraphDatabase')
    @pytest.mark.asyncio
    async def test_regression_same_uri_different_users(self, mock_graph_db):
        """
        Regression test: Same URI in different user contexts should create separate nodes
        
        This ensures that http://example.com/entity for user1 is completely separate
        from http://example.com/entity for user2.
        """
        taskgroup_mock = MagicMock()
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        
        processor = StorageProcessor(taskgroup=taskgroup_mock)
        
        # Same URI for different users
        shared_uri = "http://example.com/shared_entity"
        
        message_user1 = Triples(
            metadata=Metadata(user="user1", collection="coll1"),
            triples=[
                Triple(
                    s=Value(value=shared_uri, is_uri=True),
                    p=Value(value="http://example.com/p", is_uri=True),
                    o=Value(value="user1_value", is_uri=False)
                )
            ]
        )
        
        message_user2 = Triples(
            metadata=Metadata(user="user2", collection="coll2"),
            triples=[
                Triple(
                    s=Value(value=shared_uri, is_uri=True),
                    p=Value(value="http://example.com/p", is_uri=True),
                    o=Value(value="user2_value", is_uri=False)
                )
            ]
        )
        
        # Mock execute_query
        mock_summary = MagicMock()
        mock_summary.counters.nodes_created = 1
        mock_summary.result_available_after = 10
        mock_driver.execute_query.return_value.summary = mock_summary
        
        await processor.store_triples(message_user1)
        await processor.store_triples(message_user2)
        
        # Verify two separate nodes were created with same URI but different user/collection
        user1_node_call = call(
            "MERGE (n:Node {uri: $uri, user: $user, collection: $collection})",
            uri=shared_uri,
            user="user1",
            collection="coll1",
            database_='neo4j'
        )
        
        user2_node_call = call(
            "MERGE (n:Node {uri: $uri, user: $user, collection: $collection})",
            uri=shared_uri,
            user="user2",
            collection="coll2",
            database_='neo4j'
        )
        
        mock_driver.execute_query.assert_has_calls([user1_node_call, user2_node_call], any_order=True)