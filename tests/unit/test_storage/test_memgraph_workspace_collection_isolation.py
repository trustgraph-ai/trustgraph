"""
Tests for Memgraph workspace/collection isolation in storage service.
"""

import pytest
from unittest.mock import MagicMock, patch

from trustgraph.storage.triples.memgraph.write import Processor


class TestMemgraphWorkspaceCollectionIsolation:
    """Test cases for Memgraph storage service with workspace/collection isolation"""

    @patch('trustgraph.storage.triples.memgraph.write.GraphDatabase')
    def test_storage_creates_indexes_with_workspace_collection(self, mock_graph_db):
        """Test that storage creates both legacy and workspace/collection indexes"""
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session

        processor = Processor(taskgroup=MagicMock())

        # 4 legacy + 4 workspace/collection = 8 total
        assert mock_session.run.call_count == 8

        expected_calls = [
            "CREATE INDEX ON :Node",
            "CREATE INDEX ON :Node(uri)",
            "CREATE INDEX ON :Literal",
            "CREATE INDEX ON :Literal(value)",
            "CREATE INDEX ON :Node(workspace)",
            "CREATE INDEX ON :Node(collection)",
            "CREATE INDEX ON :Literal(workspace)",
            "CREATE INDEX ON :Literal(collection)"
        ]

        for expected_call in expected_calls:
            mock_session.run.assert_any_call(expected_call)

    @patch('trustgraph.storage.triples.memgraph.write.GraphDatabase')
    @pytest.mark.asyncio
    async def test_store_triples_with_workspace_collection(self, mock_graph_db):
        """Test that store_triples includes workspace/collection in all operations"""
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session

        mock_result = MagicMock()
        mock_summary = MagicMock()
        mock_summary.counters.nodes_created = 1
        mock_summary.result_available_after = 10
        mock_result.summary = mock_summary
        mock_driver.execute_query.return_value = mock_result

        processor = Processor(taskgroup=MagicMock())

        from trustgraph.schema import IRI
        triple = MagicMock()
        triple.s.type = IRI
        triple.s.iri = "http://example.com/subject"
        triple.p.type = IRI
        triple.p.iri = "http://example.com/predicate"
        triple.o.type = IRI
        triple.o.iri = "http://example.com/object"

        mock_message = MagicMock()
        mock_message.triples = [triple]
        mock_message.metadata.collection = "test_collection"

        with patch.object(processor, 'collection_exists', return_value=True):
            await processor.store_triples("test_workspace", mock_message)

        # create_node (subject), create_node (object), relate_node = 3 calls
        assert mock_driver.execute_query.call_count == 3

        for c in mock_driver.execute_query.call_args_list:
            kwargs = c.kwargs
            assert kwargs['workspace'] == "test_workspace"
            assert kwargs['collection'] == "test_collection"

    @patch('trustgraph.storage.triples.memgraph.write.GraphDatabase')
    @pytest.mark.asyncio
    async def test_store_triples_with_default_collection(self, mock_graph_db):
        """Test that default collection is used when not provided in metadata"""
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session

        mock_result = MagicMock()
        mock_summary = MagicMock()
        mock_summary.counters.nodes_created = 1
        mock_summary.result_available_after = 10
        mock_result.summary = mock_summary
        mock_driver.execute_query.return_value = mock_result

        processor = Processor(taskgroup=MagicMock())

        from trustgraph.schema import IRI, LITERAL
        triple = MagicMock()
        triple.s.type = IRI
        triple.s.iri = "http://example.com/subject"
        triple.p.type = IRI
        triple.p.iri = "http://example.com/predicate"
        triple.o.type = LITERAL
        triple.o.value = "literal_value"

        mock_message = MagicMock()
        mock_message.triples = [triple]
        mock_message.metadata.collection = None

        with patch.object(processor, 'collection_exists', return_value=True):
            await processor.store_triples("default", mock_message)

        for c in mock_driver.execute_query.call_args_list:
            kwargs = c.kwargs
            assert kwargs['workspace'] == "default"
            assert kwargs['collection'] == "default"

    @patch('trustgraph.storage.triples.memgraph.write.GraphDatabase')
    def test_create_node_includes_workspace_collection(self, mock_graph_db):
        """Test that create_node includes workspace/collection properties"""
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session

        mock_result = MagicMock()
        mock_summary = MagicMock()
        mock_summary.counters.nodes_created = 1
        mock_summary.result_available_after = 10
        mock_result.summary = mock_summary
        mock_driver.execute_query.return_value = mock_result

        processor = Processor(taskgroup=MagicMock())

        processor.create_node("http://example.com/node", "test_workspace", "test_collection")

        mock_driver.execute_query.assert_called_with(
            "MERGE (n:Node {uri: $uri, workspace: $workspace, collection: $collection})",
            uri="http://example.com/node",
            workspace="test_workspace",
            collection="test_collection",
            database_="memgraph"
        )

    @patch('trustgraph.storage.triples.memgraph.write.GraphDatabase')
    def test_create_literal_includes_workspace_collection(self, mock_graph_db):
        """Test that create_literal includes workspace/collection properties"""
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session

        mock_result = MagicMock()
        mock_summary = MagicMock()
        mock_summary.counters.nodes_created = 1
        mock_summary.result_available_after = 10
        mock_result.summary = mock_summary
        mock_driver.execute_query.return_value = mock_result

        processor = Processor(taskgroup=MagicMock())

        processor.create_literal("test_value", "test_workspace", "test_collection")

        mock_driver.execute_query.assert_called_with(
            "MERGE (n:Literal {value: $value, workspace: $workspace, collection: $collection})",
            value="test_value",
            workspace="test_workspace",
            collection="test_collection",
            database_="memgraph"
        )

    @patch('trustgraph.storage.triples.memgraph.write.GraphDatabase')
    def test_relate_node_includes_workspace_collection(self, mock_graph_db):
        """Test that relate_node includes workspace/collection properties"""
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session

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
            "test_workspace",
            "test_collection"
        )

        mock_driver.execute_query.assert_called_with(
            "MATCH (src:Node {uri: $src, workspace: $workspace, collection: $collection}) "
            "MATCH (dest:Node {uri: $dest, workspace: $workspace, collection: $collection}) "
            "MERGE (src)-[:Rel {uri: $uri, workspace: $workspace, collection: $collection}]->(dest)",
            src="http://example.com/subject",
            dest="http://example.com/object",
            uri="http://example.com/predicate",
            workspace="test_workspace",
            collection="test_collection",
            database_="memgraph"
        )

    @patch('trustgraph.storage.triples.memgraph.write.GraphDatabase')
    def test_relate_literal_includes_workspace_collection(self, mock_graph_db):
        """Test that relate_literal includes workspace/collection properties"""
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session

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
            "test_workspace",
            "test_collection"
        )

        mock_driver.execute_query.assert_called_with(
            "MATCH (src:Node {uri: $src, workspace: $workspace, collection: $collection}) "
            "MATCH (dest:Literal {value: $dest, workspace: $workspace, collection: $collection}) "
            "MERGE (src)-[:Rel {uri: $uri, workspace: $workspace, collection: $collection}]->(dest)",
            src="http://example.com/subject",
            dest="literal_value",
            uri="http://example.com/predicate",
            workspace="test_workspace",
            collection="test_collection",
            database_="memgraph"
        )

    def test_add_args_includes_memgraph_parameters(self):
        """Test that add_args properly configures Memgraph-specific parameters"""
        from argparse import ArgumentParser

        parser = ArgumentParser()

        with patch('trustgraph.storage.triples.memgraph.write.TriplesStoreService.add_args') as mock_parent_add_args:
            Processor.add_args(parser)
            mock_parent_add_args.assert_called_once()

        args = parser.parse_args([])

        assert hasattr(args, 'graph_host')
        assert args.graph_host == 'bolt://memgraph:7687'
        assert hasattr(args, 'username')
        assert args.username == 'memgraph'
        assert hasattr(args, 'password')
        assert args.password == 'password'
        assert hasattr(args, 'database')
        assert args.database == 'memgraph'


class TestMemgraphWorkspaceCollectionRegression:
    """Regression tests to ensure workspace/collection isolation prevents data leakage"""

    @patch('trustgraph.storage.triples.memgraph.write.GraphDatabase')
    @pytest.mark.asyncio
    async def test_regression_no_cross_workspace_data_access(self, mock_graph_db):
        """Regression test: Ensure workspaces cannot access each other's data"""
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session

        mock_result = MagicMock()
        mock_summary = MagicMock()
        mock_summary.counters.nodes_created = 1
        mock_summary.result_available_after = 10
        mock_result.summary = mock_summary
        mock_driver.execute_query.return_value = mock_result

        processor = Processor(taskgroup=MagicMock())

        from trustgraph.schema import IRI, LITERAL
        triple = MagicMock()
        triple.s.type = IRI
        triple.s.iri = "http://example.com/subject"
        triple.p.type = IRI
        triple.p.iri = "http://example.com/predicate"
        triple.o.type = LITERAL
        triple.o.value = "ws1_data"

        message_ws1 = MagicMock()
        message_ws1.triples = [triple]
        message_ws1.metadata.collection = "collection1"

        with patch.object(processor, 'collection_exists', return_value=True):
            await processor.store_triples("workspace1", message_ws1)

        for c in mock_driver.execute_query.call_args_list:
            kwargs = c.kwargs
            if 'workspace' in kwargs:
                assert kwargs['workspace'] == "workspace1"
                assert kwargs['collection'] == "collection1"

    @patch('trustgraph.storage.triples.memgraph.write.GraphDatabase')
    @pytest.mark.asyncio
    async def test_regression_same_uri_different_workspaces(self, mock_graph_db):
        """Regression test: Same URI can exist in different workspaces without conflict"""
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session

        mock_result = MagicMock()
        mock_summary = MagicMock()
        mock_summary.counters.nodes_created = 1
        mock_summary.result_available_after = 10
        mock_result.summary = mock_summary
        mock_driver.execute_query.return_value = mock_result

        processor = Processor(taskgroup=MagicMock())

        processor.create_node("http://example.com/same-uri", "workspace1", "collection1")
        processor.create_node("http://example.com/same-uri", "workspace2", "collection2")

        calls = mock_driver.execute_query.call_args_list[-2:]

        k1 = calls[0].kwargs
        k2 = calls[1].kwargs

        assert k1['workspace'] == "workspace1" and k1['collection'] == "collection1"
        assert k2['workspace'] == "workspace2" and k2['collection'] == "collection2"

        assert k1['uri'] == k2['uri'] == "http://example.com/same-uri"
