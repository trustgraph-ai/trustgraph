"""
Tests for Neo4j user/collection isolation in query service
"""

import pytest
from unittest.mock import MagicMock, patch

from trustgraph.query.triples.neo4j.service import Processor
from trustgraph.schema import TriplesQueryRequest, Term, IRI, LITERAL


class TestNeo4jQueryUserCollectionIsolation:
    """Test cases for Neo4j query service with user/collection isolation"""

    @patch('trustgraph.query.triples.neo4j.service.GraphDatabase')
    @pytest.mark.asyncio
    async def test_spo_query_with_user_collection(self, mock_graph_db):
        """Test SPO query pattern includes user/collection filtering"""
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        
        processor = Processor(taskgroup=MagicMock())
        
        query = TriplesQueryRequest(
            user="test_user",
            collection="test_collection",
            s=Term(type=IRI, iri="http://example.com/s"),
            p=Term(type=IRI, iri="http://example.com/p"),
            o=Term(type=LITERAL, value="test_object"),
            limit=10
        )

        mock_driver.execute_query.return_value = ([], MagicMock(), MagicMock())

        await processor.query_triples(query)

        # Verify SPO query for literal includes user/collection
        expected_query = (
            "MATCH (src:Node {uri: $src, user: $user, collection: $collection})-"
            "[rel:Rel {uri: $rel, user: $user, collection: $collection}]->"
            "(dest:Literal {value: $value, user: $user, collection: $collection}) "
            "RETURN $src as src "
            "LIMIT 10"
        )
        
        mock_driver.execute_query.assert_any_call(
            expected_query,
            src="http://example.com/s",
            rel="http://example.com/p",
            value="test_object",
            user="test_user",
            collection="test_collection",
            database_='neo4j'
        )

    @patch('trustgraph.query.triples.neo4j.service.GraphDatabase')
    @pytest.mark.asyncio
    async def test_sp_query_with_user_collection(self, mock_graph_db):
        """Test SP query pattern includes user/collection filtering"""
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        
        processor = Processor(taskgroup=MagicMock())
        
        query = TriplesQueryRequest(
            user="test_user",
            collection="test_collection",
            s=Term(type=IRI, iri="http://example.com/s"),
            p=Term(type=IRI, iri="http://example.com/p"),
            o=None,
            limit=10
        )

        mock_driver.execute_query.return_value = ([], MagicMock(), MagicMock())

        await processor.query_triples(query)

        # Verify SP query for literals includes user/collection
        expected_literal_query = (
            "MATCH (src:Node {uri: $src, user: $user, collection: $collection})-"
            "[rel:Rel {uri: $rel, user: $user, collection: $collection}]->"
            "(dest:Literal {user: $user, collection: $collection}) "
            "RETURN dest.value as dest "
            "LIMIT 10"
        )

        mock_driver.execute_query.assert_any_call(
            expected_literal_query,
            src="http://example.com/s",
            rel="http://example.com/p",
            user="test_user",
            collection="test_collection",
            database_='neo4j'
        )

        # Verify SP query for nodes includes user/collection
        expected_node_query = (
            "MATCH (src:Node {uri: $src, user: $user, collection: $collection})-"
            "[rel:Rel {uri: $rel, user: $user, collection: $collection}]->"
            "(dest:Node {user: $user, collection: $collection}) "
            "RETURN dest.uri as dest "
            "LIMIT 10"
        )
        
        mock_driver.execute_query.assert_any_call(
            expected_node_query,
            src="http://example.com/s",
            rel="http://example.com/p",
            user="test_user",
            collection="test_collection",
            database_='neo4j'
        )

    @patch('trustgraph.query.triples.neo4j.service.GraphDatabase')
    @pytest.mark.asyncio
    async def test_so_query_with_user_collection(self, mock_graph_db):
        """Test SO query pattern includes user/collection filtering"""
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        
        processor = Processor(taskgroup=MagicMock())
        
        query = TriplesQueryRequest(
            user="test_user",
            collection="test_collection",
            s=Term(type=IRI, iri="http://example.com/s"),
            p=None,
            o=Term(type=IRI, iri="http://example.com/o"),
            limit=10
        )

        mock_driver.execute_query.return_value = ([], MagicMock(), MagicMock())

        await processor.query_triples(query)

        # Verify SO query for nodes includes user/collection
        expected_query = (
            "MATCH (src:Node {uri: $src, user: $user, collection: $collection})-"
            "[rel:Rel {user: $user, collection: $collection}]->"
            "(dest:Node {uri: $uri, user: $user, collection: $collection}) "
            "RETURN rel.uri as rel "
            "LIMIT 10"
        )
        
        mock_driver.execute_query.assert_any_call(
            expected_query,
            src="http://example.com/s",
            uri="http://example.com/o",
            user="test_user",
            collection="test_collection",
            database_='neo4j'
        )

    @patch('trustgraph.query.triples.neo4j.service.GraphDatabase')
    @pytest.mark.asyncio
    async def test_s_only_query_with_user_collection(self, mock_graph_db):
        """Test S-only query pattern includes user/collection filtering"""
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        
        processor = Processor(taskgroup=MagicMock())
        
        query = TriplesQueryRequest(
            user="test_user",
            collection="test_collection",
            s=Term(type=IRI, iri="http://example.com/s"),
            p=None,
            o=None,
            limit=10
        )

        mock_driver.execute_query.return_value = ([], MagicMock(), MagicMock())

        await processor.query_triples(query)

        # Verify S query includes user/collection
        expected_query = (
            "MATCH (src:Node {uri: $src, user: $user, collection: $collection})-"
            "[rel:Rel {user: $user, collection: $collection}]->"
            "(dest:Literal {user: $user, collection: $collection}) "
            "RETURN rel.uri as rel, dest.value as dest "
            "LIMIT 10"
        )

        mock_driver.execute_query.assert_any_call(
            expected_query,
            src="http://example.com/s",
            user="test_user",
            collection="test_collection",
            database_='neo4j'
        )

    @patch('trustgraph.query.triples.neo4j.service.GraphDatabase')
    @pytest.mark.asyncio
    async def test_po_query_with_user_collection(self, mock_graph_db):
        """Test PO query pattern includes user/collection filtering"""
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        
        processor = Processor(taskgroup=MagicMock())
        
        query = TriplesQueryRequest(
            user="test_user",
            collection="test_collection",
            s=None,
            p=Term(type=IRI, iri="http://example.com/p"),
            o=Term(type=LITERAL, value="literal"),
            limit=10
        )

        mock_driver.execute_query.return_value = ([], MagicMock(), MagicMock())

        await processor.query_triples(query)

        # Verify PO query for literals includes user/collection
        expected_query = (
            "MATCH (src:Node {user: $user, collection: $collection})-"
            "[rel:Rel {uri: $uri, user: $user, collection: $collection}]->"
            "(dest:Literal {value: $value, user: $user, collection: $collection}) "
            "RETURN src.uri as src "
            "LIMIT 10"
        )
        
        mock_driver.execute_query.assert_any_call(
            expected_query,
            uri="http://example.com/p",
            value="literal",
            user="test_user",
            collection="test_collection",
            database_='neo4j'
        )

    @patch('trustgraph.query.triples.neo4j.service.GraphDatabase')
    @pytest.mark.asyncio
    async def test_p_only_query_with_user_collection(self, mock_graph_db):
        """Test P-only query pattern includes user/collection filtering"""
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        
        processor = Processor(taskgroup=MagicMock())
        
        query = TriplesQueryRequest(
            user="test_user",
            collection="test_collection",
            s=None,
            p=Term(type=IRI, iri="http://example.com/p"),
            o=None,
            limit=10
        )

        mock_driver.execute_query.return_value = ([], MagicMock(), MagicMock())

        await processor.query_triples(query)

        # Verify P query includes user/collection
        expected_query = (
            "MATCH (src:Node {user: $user, collection: $collection})-"
            "[rel:Rel {uri: $uri, user: $user, collection: $collection}]->"
            "(dest:Literal {user: $user, collection: $collection}) "
            "RETURN src.uri as src, dest.value as dest "
            "LIMIT 10"
        )
        
        mock_driver.execute_query.assert_any_call(
            expected_query,
            uri="http://example.com/p",
            user="test_user",
            collection="test_collection",
            database_='neo4j'
        )

    @patch('trustgraph.query.triples.neo4j.service.GraphDatabase')
    @pytest.mark.asyncio
    async def test_o_only_query_with_user_collection(self, mock_graph_db):
        """Test O-only query pattern includes user/collection filtering"""
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        
        processor = Processor(taskgroup=MagicMock())
        
        query = TriplesQueryRequest(
            user="test_user",
            collection="test_collection",
            s=None,
            p=None,
            o=Term(type=LITERAL, value="test_value"),
            limit=10
        )

        mock_driver.execute_query.return_value = ([], MagicMock(), MagicMock())

        await processor.query_triples(query)

        # Verify O query for literals includes user/collection
        expected_query = (
            "MATCH (src:Node {user: $user, collection: $collection})-"
            "[rel:Rel {user: $user, collection: $collection}]->"
            "(dest:Literal {value: $value, user: $user, collection: $collection}) "
            "RETURN src.uri as src, rel.uri as rel "
            "LIMIT 10"
        )
        
        mock_driver.execute_query.assert_any_call(
            expected_query,
            value="test_value",
            user="test_user",
            collection="test_collection",
            database_='neo4j'
        )

    @patch('trustgraph.query.triples.neo4j.service.GraphDatabase')
    @pytest.mark.asyncio
    async def test_wildcard_query_with_user_collection(self, mock_graph_db):
        """Test wildcard query (all None) includes user/collection filtering"""
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        
        processor = Processor(taskgroup=MagicMock())
        
        query = TriplesQueryRequest(
            user="test_user",
            collection="test_collection",
            s=None,
            p=None,
            o=None,
            limit=10
        )

        mock_driver.execute_query.return_value = ([], MagicMock(), MagicMock())

        await processor.query_triples(query)

        # Verify wildcard query for literals includes user/collection
        expected_literal_query = (
            "MATCH (src:Node {user: $user, collection: $collection})-"
            "[rel:Rel {user: $user, collection: $collection}]->"
            "(dest:Literal {user: $user, collection: $collection}) "
            "RETURN src.uri as src, rel.uri as rel, dest.value as dest "
            "LIMIT 10"
        )

        mock_driver.execute_query.assert_any_call(
            expected_literal_query,
            user="test_user",
            collection="test_collection",
            database_='neo4j'
        )

        # Verify wildcard query for nodes includes user/collection
        expected_node_query = (
            "MATCH (src:Node {user: $user, collection: $collection})-"
            "[rel:Rel {user: $user, collection: $collection}]->"
            "(dest:Node {user: $user, collection: $collection}) "
            "RETURN src.uri as src, rel.uri as rel, dest.uri as dest "
            "LIMIT 10"
        )
        
        mock_driver.execute_query.assert_any_call(
            expected_node_query,
            user="test_user",
            collection="test_collection",
            database_='neo4j'
        )

    @patch('trustgraph.query.triples.neo4j.service.GraphDatabase')
    @pytest.mark.asyncio
    async def test_query_with_defaults_when_not_provided(self, mock_graph_db):
        """Test that defaults are used when user/collection not provided"""
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        
        processor = Processor(taskgroup=MagicMock())
        
        # Query without user/collection fields
        query = TriplesQueryRequest(
            s=Term(type=IRI, iri="http://example.com/s"),
            p=None,
            o=None,
            limit=10
        )
        
        mock_driver.execute_query.return_value = ([], MagicMock(), MagicMock())
        
        await processor.query_triples(query)
        
        # Verify defaults were used
        calls = mock_driver.execute_query.call_args_list
        for call in calls:
            if 'user' in call.kwargs:
                assert call.kwargs['user'] == 'default'
            if 'collection' in call.kwargs:
                assert call.kwargs['collection'] == 'default'

    @patch('trustgraph.query.triples.neo4j.service.GraphDatabase')
    @pytest.mark.asyncio
    async def test_results_properly_converted_to_triples(self, mock_graph_db):
        """Test that query results are properly converted to Triple objects"""
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        
        processor = Processor(taskgroup=MagicMock())
        
        query = TriplesQueryRequest(
            user="test_user",
            collection="test_collection",
            s=Term(type=IRI, iri="http://example.com/s"),
            p=None,
            o=None,
            limit=10
        )

        # Mock some results
        mock_record1 = MagicMock()
        mock_record1.data.return_value = {
            "rel": "http://example.com/p1",
            "dest": "literal_value"
        }

        mock_record2 = MagicMock()
        mock_record2.data.return_value = {
            "rel": "http://example.com/p2",
            "dest": "http://example.com/o"
        }

        # Return results for literal query, empty for node query
        mock_driver.execute_query.side_effect = [
            ([mock_record1], MagicMock(), MagicMock()),  # Literal query
            ([mock_record2], MagicMock(), MagicMock())   # Node query
        ]

        result = await processor.query_triples(query)
        
        # Verify results are proper Triple objects
        assert len(result) == 2
        
        # First triple (literal object)
        assert result[0].s.iri == "http://example.com/s"
        assert result[0].s.type == IRI
        assert result[0].p.iri == "http://example.com/p1"
        assert result[0].p.type == IRI
        assert result[0].o.value == "literal_value"
        assert result[0].o.type == LITERAL

        # Second triple (URI object)
        assert result[1].s.iri == "http://example.com/s"
        assert result[1].s.type == IRI
        assert result[1].p.iri == "http://example.com/p2"
        assert result[1].p.type == IRI
        assert result[1].o.iri == "http://example.com/o"
        assert result[1].o.type == IRI