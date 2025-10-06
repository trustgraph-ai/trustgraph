"""
Tests for Memgraph user/collection isolation in storage service
"""

import pytest
from unittest.mock import MagicMock, patch

from trustgraph.storage.triples.memgraph.write import Processor


class TestMemgraphUserCollectionIsolation:
    """Test cases for Memgraph storage service with user/collection isolation"""

    @patch('trustgraph.storage.triples.memgraph.write.GraphDatabase')
    def test_storage_creates_indexes_with_user_collection(self, mock_graph_db):
        """Test that storage creates both legacy and user/collection indexes"""
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        
        processor = Processor(taskgroup=MagicMock())
        
        # Verify all indexes were attempted (4 legacy + 4 user/collection = 8 total)
        assert mock_session.run.call_count == 8
        
        # Check some specific index creation calls
        expected_calls = [
            "CREATE INDEX ON :Node",
            "CREATE INDEX ON :Node(uri)",
            "CREATE INDEX ON :Literal",
            "CREATE INDEX ON :Literal(value)",
            "CREATE INDEX ON :Node(user)",
            "CREATE INDEX ON :Node(collection)",
            "CREATE INDEX ON :Literal(user)",
            "CREATE INDEX ON :Literal(collection)"
        ]
        
        for expected_call in expected_calls:
            mock_session.run.assert_any_call(expected_call)

    @patch('trustgraph.storage.triples.memgraph.write.GraphDatabase')
    @pytest.mark.asyncio
    async def test_store_triples_with_user_collection(self, mock_graph_db):
        """Test that store_triples includes user/collection in all operations"""
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session

        # Mock execute_query response
        mock_result = MagicMock()
        mock_summary = MagicMock()
        mock_summary.counters.nodes_created = 1
        mock_summary.result_available_after = 10
        mock_result.summary = mock_summary
        mock_driver.execute_query.return_value = mock_result

        processor = Processor(taskgroup=MagicMock())

        # Create mock triple with URI object
        triple = MagicMock()
        triple.s.value = "http://example.com/subject"
        triple.p.value = "http://example.com/predicate"
        triple.o.value = "http://example.com/object"
        triple.o.is_uri = True

        # Create mock message with metadata
        mock_message = MagicMock()
        mock_message.triples = [triple]
        mock_message.metadata.user = "test_user"
        mock_message.metadata.collection = "test_collection"

        # Mock collection_exists to bypass validation in unit tests
        with patch.object(processor, 'collection_exists', return_value=True):
            await processor.store_triples(mock_message)

        # Verify user/collection parameters were passed to all operations
        # Should have: create_node (subject), create_node (object), relate_node = 3 calls
        assert mock_driver.execute_query.call_count == 3

        # Check that user and collection were included in all calls
        for call in mock_driver.execute_query.call_args_list:
            call_kwargs = call.kwargs if hasattr(call, 'kwargs') else call[1]
            assert 'user' in call_kwargs
            assert 'collection' in call_kwargs
            assert call_kwargs['user'] == "test_user"
            assert call_kwargs['collection'] == "test_collection"

    @patch('trustgraph.storage.triples.memgraph.write.GraphDatabase')
    @pytest.mark.asyncio
    async def test_store_triples_with_default_user_collection(self, mock_graph_db):
        """Test that defaults are used when user/collection not provided in metadata"""
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session

        # Mock execute_query response
        mock_result = MagicMock()
        mock_summary = MagicMock()
        mock_summary.counters.nodes_created = 1
        mock_summary.result_available_after = 10
        mock_result.summary = mock_summary
        mock_driver.execute_query.return_value = mock_result

        processor = Processor(taskgroup=MagicMock())

        # Create mock triple
        triple = MagicMock()
        triple.s.value = "http://example.com/subject"
        triple.p.value = "http://example.com/predicate"
        triple.o.value = "literal_value"
        triple.o.is_uri = False

        # Create mock message without user/collection metadata
        mock_message = MagicMock()
        mock_message.triples = [triple]
        mock_message.metadata.user = None
        mock_message.metadata.collection = None

        # Mock collection_exists to bypass validation in unit tests
        with patch.object(processor, 'collection_exists', return_value=True):
            await processor.store_triples(mock_message)

        # Verify defaults were used
        for call in mock_driver.execute_query.call_args_list:
            call_kwargs = call.kwargs if hasattr(call, 'kwargs') else call[1]
            assert call_kwargs['user'] == "default"
            assert call_kwargs['collection'] == "default"

    @patch('trustgraph.storage.triples.memgraph.write.GraphDatabase')
    def test_create_node_includes_user_collection(self, mock_graph_db):
        """Test that create_node includes user/collection properties"""
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        
        # Mock execute_query response
        mock_result = MagicMock()
        mock_summary = MagicMock()
        mock_summary.counters.nodes_created = 1
        mock_summary.result_available_after = 10
        mock_result.summary = mock_summary
        mock_driver.execute_query.return_value = mock_result
        
        processor = Processor(taskgroup=MagicMock())
        
        processor.create_node("http://example.com/node", "test_user", "test_collection")
        
        mock_driver.execute_query.assert_called_with(
            "MERGE (n:Node {uri: $uri, user: $user, collection: $collection})",
            uri="http://example.com/node",
            user="test_user",
            collection="test_collection",
            database_="memgraph"
        )

    @patch('trustgraph.storage.triples.memgraph.write.GraphDatabase')
    def test_create_literal_includes_user_collection(self, mock_graph_db):
        """Test that create_literal includes user/collection properties"""
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        
        # Mock execute_query response
        mock_result = MagicMock()
        mock_summary = MagicMock()
        mock_summary.counters.nodes_created = 1
        mock_summary.result_available_after = 10
        mock_result.summary = mock_summary
        mock_driver.execute_query.return_value = mock_result
        
        processor = Processor(taskgroup=MagicMock())
        
        processor.create_literal("test_value", "test_user", "test_collection")
        
        mock_driver.execute_query.assert_called_with(
            "MERGE (n:Literal {value: $value, user: $user, collection: $collection})",
            value="test_value",
            user="test_user",
            collection="test_collection",
            database_="memgraph"
        )

    @patch('trustgraph.storage.triples.memgraph.write.GraphDatabase')
    def test_relate_node_includes_user_collection(self, mock_graph_db):
        """Test that relate_node includes user/collection properties"""
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        
        # Mock execute_query response
        mock_result = MagicMock()
        mock_summary = MagicMock()
        mock_summary.counters.nodes_created = 0
        mock_summary.result_available_after = 10
        mock_result.summary = mock_summary
        mock_driver.execute_query.return_value = mock_result
        
        processor = Processor(taskgroup=MagicMock())
        
        processor.relate_node(
            "http://example.com/subject",
            "http://example.com/predicate", 
            "http://example.com/object",
            "test_user",
            "test_collection"
        )
        
        mock_driver.execute_query.assert_called_with(
            "MATCH (src:Node {uri: $src, user: $user, collection: $collection}) "
            "MATCH (dest:Node {uri: $dest, user: $user, collection: $collection}) "
            "MERGE (src)-[:Rel {uri: $uri, user: $user, collection: $collection}]->(dest)",
            src="http://example.com/subject",
            dest="http://example.com/object",
            uri="http://example.com/predicate",
            user="test_user",
            collection="test_collection",
            database_="memgraph"
        )

    @patch('trustgraph.storage.triples.memgraph.write.GraphDatabase')
    def test_relate_literal_includes_user_collection(self, mock_graph_db):
        """Test that relate_literal includes user/collection properties"""
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        
        # Mock execute_query response
        mock_result = MagicMock()
        mock_summary = MagicMock()
        mock_summary.counters.nodes_created = 0
        mock_summary.result_available_after = 10
        mock_result.summary = mock_summary
        mock_driver.execute_query.return_value = mock_result
        
        processor = Processor(taskgroup=MagicMock())
        
        processor.relate_literal(
            "http://example.com/subject",
            "http://example.com/predicate",
            "literal_value",
            "test_user", 
            "test_collection"
        )
        
        mock_driver.execute_query.assert_called_with(
            "MATCH (src:Node {uri: $src, user: $user, collection: $collection}) "
            "MATCH (dest:Literal {value: $dest, user: $user, collection: $collection}) "
            "MERGE (src)-[:Rel {uri: $uri, user: $user, collection: $collection}]->(dest)",
            src="http://example.com/subject",
            dest="literal_value",
            uri="http://example.com/predicate",
            user="test_user",
            collection="test_collection",
            database_="memgraph"
        )

    def test_add_args_includes_memgraph_parameters(self):
        """Test that add_args properly configures Memgraph-specific parameters"""
        from argparse import ArgumentParser
        from unittest.mock import patch
        
        parser = ArgumentParser()
        
        # Mock the parent class add_args method
        with patch('trustgraph.storage.triples.memgraph.write.TriplesStoreService.add_args') as mock_parent_add_args:
            Processor.add_args(parser)
            
            # Verify parent add_args was called
            mock_parent_add_args.assert_called_once()
        
        # Verify our specific arguments were added with Memgraph defaults
        args = parser.parse_args([])
        
        assert hasattr(args, 'graph_host')
        assert args.graph_host == 'bolt://memgraph:7687'
        assert hasattr(args, 'username')
        assert args.username == 'memgraph'
        assert hasattr(args, 'password')
        assert args.password == 'password'
        assert hasattr(args, 'database')
        assert args.database == 'memgraph'


class TestMemgraphUserCollectionRegression:
    """Regression tests to ensure user/collection isolation prevents data leakage"""

    @patch('trustgraph.storage.triples.memgraph.write.GraphDatabase')
    @pytest.mark.asyncio
    async def test_regression_no_cross_user_data_access(self, mock_graph_db):
        """Regression test: Ensure users cannot access each other's data"""
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session

        # Mock execute_query response
        mock_result = MagicMock()
        mock_summary = MagicMock()
        mock_summary.counters.nodes_created = 1
        mock_summary.result_available_after = 10
        mock_result.summary = mock_summary
        mock_driver.execute_query.return_value = mock_result

        processor = Processor(taskgroup=MagicMock())

        # Store data for user1
        triple = MagicMock()
        triple.s.value = "http://example.com/subject"
        triple.p.value = "http://example.com/predicate"
        triple.o.value = "user1_data"
        triple.o.is_uri = False

        message_user1 = MagicMock()
        message_user1.triples = [triple]
        message_user1.metadata.user = "user1"
        message_user1.metadata.collection = "collection1"

        # Mock collection_exists to bypass validation in unit tests
        with patch.object(processor, 'collection_exists', return_value=True):
            await processor.store_triples(message_user1)

        # Verify that all storage operations included user1/collection1 parameters
        for call in mock_driver.execute_query.call_args_list:
            call_kwargs = call.kwargs if hasattr(call, 'kwargs') else call[1]
            if 'user' in call_kwargs:
                assert call_kwargs['user'] == "user1"
                assert call_kwargs['collection'] == "collection1"

    @patch('trustgraph.storage.triples.memgraph.write.GraphDatabase')
    @pytest.mark.asyncio
    async def test_regression_same_uri_different_users(self, mock_graph_db):
        """Regression test: Same URI can exist for different users without conflict"""
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        
        # Mock execute_query response
        mock_result = MagicMock()
        mock_summary = MagicMock()
        mock_summary.counters.nodes_created = 1
        mock_summary.result_available_after = 10
        mock_result.summary = mock_summary
        mock_driver.execute_query.return_value = mock_result
        
        processor = Processor(taskgroup=MagicMock())
        
        # Same URI for different users should create separate nodes
        processor.create_node("http://example.com/same-uri", "user1", "collection1")
        processor.create_node("http://example.com/same-uri", "user2", "collection2")
        
        # Verify both calls were made with different user/collection parameters
        calls = mock_driver.execute_query.call_args_list[-2:]  # Get last 2 calls
        
        call1_kwargs = calls[0].kwargs if hasattr(calls[0], 'kwargs') else calls[0][1]
        call2_kwargs = calls[1].kwargs if hasattr(calls[1], 'kwargs') else calls[1][1]
        
        assert call1_kwargs['user'] == "user1" and call1_kwargs['collection'] == "collection1"
        assert call2_kwargs['user'] == "user2" and call2_kwargs['collection'] == "collection2"
        
        # Both should have the same URI but different user/collection
        assert call1_kwargs['uri'] == call2_kwargs['uri'] == "http://example.com/same-uri"