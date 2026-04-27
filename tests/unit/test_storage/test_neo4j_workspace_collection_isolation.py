"""
Tests for Neo4j workspace/collection isolation in triples storage and query.
"""

import pytest
from unittest.mock import MagicMock, patch, call

from trustgraph.storage.triples.neo4j.write import Processor as StorageProcessor
from trustgraph.query.triples.neo4j.service import Processor as QueryProcessor
from trustgraph.schema import Triples, Triple, Term, Metadata, IRI, LITERAL
from trustgraph.schema import TriplesQueryRequest


class TestNeo4jWorkspaceCollectionIsolation:
    """Test cases for Neo4j workspace/collection isolation functionality"""

    @patch('trustgraph.storage.triples.neo4j.write.GraphDatabase')
    def test_storage_creates_indexes_with_workspace_collection(self, mock_graph_db):
        """Test that storage service creates compound indexes for workspace/collection"""
        taskgroup_mock = MagicMock()
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session

        processor = StorageProcessor(taskgroup=taskgroup_mock)

        expected_indexes = [
            "CREATE INDEX Node_uri FOR (n:Node) ON (n.uri)",
            "CREATE INDEX Literal_value FOR (n:Literal) ON (n.value)",
            "CREATE INDEX Rel_uri FOR ()-[r:Rel]-() ON (r.uri)",
            "CREATE INDEX node_workspace_collection_uri FOR (n:Node) ON (n.workspace, n.collection, n.uri)",
            "CREATE INDEX literal_workspace_collection_value FOR (n:Literal) ON (n.workspace, n.collection, n.value)",
            "CREATE INDEX rel_workspace FOR ()-[r:Rel]-() ON (r.workspace)",
            "CREATE INDEX rel_collection FOR ()-[r:Rel]-() ON (r.collection)"
        ]

        for expected_query in expected_indexes:
            mock_session.run.assert_any_call(expected_query)

    @patch('trustgraph.storage.triples.neo4j.write.GraphDatabase')
    @pytest.mark.asyncio
    async def test_store_triples_with_workspace_collection(self, mock_graph_db):
        """Test that triples are stored with workspace/collection properties"""
        taskgroup_mock = MagicMock()
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session

        processor = StorageProcessor(taskgroup=taskgroup_mock)

        metadata = Metadata(id="test-id", collection="test_collection")

        triple = Triple(
            s=Term(type=IRI, iri="http://example.com/subject"),
            p=Term(type=IRI, iri="http://example.com/predicate"),
            o=Term(type=LITERAL, value="literal_value")
        )

        message = Triples(metadata=metadata, triples=[triple])

        mock_summary = MagicMock()
        mock_summary.counters.nodes_created = 1
        mock_summary.result_available_after = 10
        mock_driver.execute_query.return_value.summary = mock_summary

        with patch.object(processor, 'collection_exists', return_value=True):
            await processor.store_triples("test_workspace", message)

        expected_calls = [
            call(
                "MERGE (n:Node {uri: $uri, workspace: $workspace, collection: $collection})",
                uri="http://example.com/subject",
                workspace="test_workspace",
                collection="test_collection",
                database_='neo4j'
            ),
            call(
                "MERGE (n:Literal {value: $value, workspace: $workspace, collection: $collection})",
                value="literal_value",
                workspace="test_workspace",
                collection="test_collection",
                database_='neo4j'
            ),
            call(
                "MATCH (src:Node {uri: $src, workspace: $workspace, collection: $collection}) "
                "MATCH (dest:Literal {value: $dest, workspace: $workspace, collection: $collection}) "
                "MERGE (src)-[:Rel {uri: $uri, workspace: $workspace, collection: $collection}]->(dest)",
                src="http://example.com/subject",
                dest="literal_value",
                uri="http://example.com/predicate",
                workspace="test_workspace",
                collection="test_collection",
                database_='neo4j'
            )
        ]

        for expected_call in expected_calls:
            mock_driver.execute_query.assert_any_call(*expected_call.args, **expected_call.kwargs)

    @patch('trustgraph.storage.triples.neo4j.write.GraphDatabase')
    @pytest.mark.asyncio
    async def test_store_triples_with_default_collection(self, mock_graph_db):
        """Test that default collection is used when not provided"""
        taskgroup_mock = MagicMock()
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session

        processor = StorageProcessor(taskgroup=taskgroup_mock)

        metadata = Metadata(id="test-id")

        triple = Triple(
            s=Term(type=IRI, iri="http://example.com/subject"),
            p=Term(type=IRI, iri="http://example.com/predicate"),
            o=Term(type=IRI, iri="http://example.com/object")
        )

        message = Triples(metadata=metadata, triples=[triple])

        mock_summary = MagicMock()
        mock_summary.counters.nodes_created = 1
        mock_summary.result_available_after = 10
        mock_driver.execute_query.return_value.summary = mock_summary

        with patch.object(processor, 'collection_exists', return_value=True):
            await processor.store_triples("default", message)

        mock_driver.execute_query.assert_any_call(
            "MERGE (n:Node {uri: $uri, workspace: $workspace, collection: $collection})",
            uri="http://example.com/subject",
            workspace="default",
            collection="default",
            database_='neo4j'
        )

    @patch('trustgraph.query.triples.neo4j.service.GraphDatabase')
    @pytest.mark.asyncio
    async def test_query_triples_filters_by_workspace_collection(self, mock_graph_db):
        """Test that query service filters results by workspace/collection"""
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver

        processor = QueryProcessor(taskgroup=MagicMock())

        query = TriplesQueryRequest(
            collection="test_collection",
            s=Term(type=IRI, iri="http://example.com/subject"),
            p=Term(type=IRI, iri="http://example.com/predicate"),
            o=None
        )

        mock_records = [
            MagicMock(data=lambda: {"dest": "http://example.com/object1"}),
            MagicMock(data=lambda: {"dest": "literal_value"})
        ]

        mock_driver.execute_query.return_value = (mock_records, MagicMock(), MagicMock())

        await processor.query_triples("test_workspace", query)

        expected_literal_query = (
            "MATCH (src:Node {uri: $src, workspace: $workspace, collection: $collection})-"
            "[rel:Rel {uri: $rel, workspace: $workspace, collection: $collection}]->"
            "(dest:Literal {workspace: $workspace, collection: $collection}) "
            "RETURN dest.value as dest"
        )

        calls = mock_driver.execute_query.call_args_list
        assert any(
            expected_literal_query in str(c) and
            "workspace='test_workspace'" in str(c) and
            "collection='test_collection'" in str(c)
            for c in calls
        )

    @patch('trustgraph.query.triples.neo4j.service.GraphDatabase')
    @pytest.mark.asyncio
    async def test_query_triples_with_default_collection(self, mock_graph_db):
        """Test that query service uses default collection when not provided"""
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver

        processor = QueryProcessor(taskgroup=MagicMock())

        query = TriplesQueryRequest(s=None, p=None, o=None)

        mock_driver.execute_query.return_value = ([], MagicMock(), MagicMock())

        await processor.query_triples("default", query)

        calls = mock_driver.execute_query.call_args_list
        assert any(
            "workspace='default'" in str(c) and "collection='default'" in str(c)
            for c in calls
        )

    @patch('trustgraph.storage.triples.neo4j.write.GraphDatabase')
    @pytest.mark.asyncio
    async def test_data_isolation_between_workspaces(self, mock_graph_db):
        """Test that data from different workspaces is properly isolated"""
        taskgroup_mock = MagicMock()
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session

        processor = StorageProcessor(taskgroup=taskgroup_mock)

        message_ws1 = Triples(
            metadata=Metadata(collection="coll1"),
            triples=[
                Triple(
                    s=Term(type=IRI, iri="http://example.com/ws1/subject"),
                    p=Term(type=IRI, iri="http://example.com/predicate"),
                    o=Term(type=LITERAL, value="ws1_data")
                )
            ]
        )

        message_ws2 = Triples(
            metadata=Metadata(collection="coll2"),
            triples=[
                Triple(
                    s=Term(type=IRI, iri="http://example.com/ws2/subject"),
                    p=Term(type=IRI, iri="http://example.com/predicate"),
                    o=Term(type=LITERAL, value="ws2_data")
                )
            ]
        )

        mock_summary = MagicMock()
        mock_summary.counters.nodes_created = 1
        mock_summary.result_available_after = 10
        mock_driver.execute_query.return_value.summary = mock_summary

        with patch.object(processor, 'collection_exists', return_value=True):
            await processor.store_triples("workspace1", message_ws1)
            await processor.store_triples("workspace2", message_ws2)

        mock_driver.execute_query.assert_any_call(
            "MERGE (n:Literal {value: $value, workspace: $workspace, collection: $collection})",
            value="ws1_data",
            workspace="workspace1",
            collection="coll1",
            database_='neo4j'
        )

        mock_driver.execute_query.assert_any_call(
            "MERGE (n:Literal {value: $value, workspace: $workspace, collection: $collection})",
            value="ws2_data",
            workspace="workspace2",
            collection="coll2",
            database_='neo4j'
        )

    @patch('trustgraph.query.triples.neo4j.service.GraphDatabase')
    @pytest.mark.asyncio
    async def test_wildcard_query_respects_workspace_collection(self, mock_graph_db):
        """Test that wildcard queries still filter by workspace/collection"""
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver

        processor = QueryProcessor(taskgroup=MagicMock())

        query = TriplesQueryRequest(
            collection="test_collection",
            s=None, p=None, o=None,
        )

        mock_driver.execute_query.return_value = ([], MagicMock(), MagicMock())

        await processor.query_triples("test_workspace", query)

        wildcard_query = (
            "MATCH (src:Node {workspace: $workspace, collection: $collection})-"
            "[rel:Rel {workspace: $workspace, collection: $collection}]->"
            "(dest:Literal {workspace: $workspace, collection: $collection}) "
            "RETURN src.uri as src, rel.uri as rel, dest.value as dest"
        )

        calls = mock_driver.execute_query.call_args_list
        assert any(
            wildcard_query in str(c) and
            "workspace='test_workspace'" in str(c) and
            "collection='test_collection'" in str(c)
            for c in calls
        )

    def test_add_args_includes_neo4j_parameters(self):
        """Test that add_args includes Neo4j-specific parameters"""
        from argparse import ArgumentParser

        parser = ArgumentParser()

        with patch('trustgraph.storage.triples.neo4j.write.TriplesStoreService.add_args'):
            StorageProcessor.add_args(parser)

        args = parser.parse_args([])

        assert hasattr(args, 'graph_host')
        assert hasattr(args, 'username')
        assert hasattr(args, 'password')
        assert hasattr(args, 'database')

        assert args.graph_host == 'bolt://neo4j:7687'
        assert args.username == 'neo4j'
        assert args.password == 'password'
        assert args.database == 'neo4j'


class TestNeo4jWorkspaceCollectionRegression:
    """Regression tests to ensure workspace/collection isolation prevents data leaks"""

    @patch('trustgraph.query.triples.neo4j.service.GraphDatabase')
    @pytest.mark.asyncio
    async def test_regression_no_cross_workspace_data_access(self, mock_graph_db):
        """
        Regression test: Ensure workspace1 cannot access workspace2's data.

        Guards against a bug where all data shared the same Neo4j graph
        space, causing data contamination between workspaces.
        """
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver

        processor = QueryProcessor(taskgroup=MagicMock())

        query_ws1 = TriplesQueryRequest(
            collection="collection1",
            s=None, p=None, o=None
        )

        mock_driver.execute_query.return_value = ([], MagicMock(), MagicMock())

        result = await processor.query_triples("workspace1", query_ws1)

        assert len(result) == 0

        calls = mock_driver.execute_query.call_args_list
        for c in calls:
            query_str = str(c)
            if "MATCH" in query_str:
                assert "workspace: $workspace" in query_str or "workspace='workspace1'" in query_str
                assert "collection: $collection" in query_str or "collection='collection1'" in query_str

    @patch('trustgraph.storage.triples.neo4j.write.GraphDatabase')
    @pytest.mark.asyncio
    async def test_regression_same_uri_different_workspaces(self, mock_graph_db):
        """
        Regression test: Same URI in different workspace contexts should create separate nodes.

        Ensures http://example.com/entity in workspace1 is completely
        separate from the same URI in workspace2.
        """
        taskgroup_mock = MagicMock()
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session

        processor = StorageProcessor(taskgroup=taskgroup_mock)

        shared_uri = "http://example.com/shared_entity"

        message_ws1 = Triples(
            metadata=Metadata(collection="coll1"),
            triples=[
                Triple(
                    s=Term(type=IRI, iri=shared_uri),
                    p=Term(type=IRI, iri="http://example.com/p"),
                    o=Term(type=LITERAL, value="ws1_value")
                )
            ]
        )

        message_ws2 = Triples(
            metadata=Metadata(collection="coll2"),
            triples=[
                Triple(
                    s=Term(type=IRI, iri=shared_uri),
                    p=Term(type=IRI, iri="http://example.com/p"),
                    o=Term(type=LITERAL, value="ws2_value")
                )
            ]
        )

        mock_summary = MagicMock()
        mock_summary.counters.nodes_created = 1
        mock_summary.result_available_after = 10
        mock_driver.execute_query.return_value.summary = mock_summary

        with patch.object(processor, 'collection_exists', return_value=True):
            await processor.store_triples("workspace1", message_ws1)
            await processor.store_triples("workspace2", message_ws2)

        ws1_node_call = call(
            "MERGE (n:Node {uri: $uri, workspace: $workspace, collection: $collection})",
            uri=shared_uri,
            workspace="workspace1",
            collection="coll1",
            database_='neo4j'
        )

        ws2_node_call = call(
            "MERGE (n:Node {uri: $uri, workspace: $workspace, collection: $collection})",
            uri=shared_uri,
            workspace="workspace2",
            collection="coll2",
            database_='neo4j'
        )

        mock_driver.execute_query.assert_has_calls([ws1_node_call, ws2_node_call], any_order=True)
