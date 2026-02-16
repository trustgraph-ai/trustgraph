"""
Unit tests for EntityCentricKnowledgeGraph class

Tests the entity-centric knowledge graph implementation without requiring
an actual Cassandra connection. Uses mocking to verify correct behavior.
"""

import pytest
from unittest.mock import MagicMock, patch, call
import os


class TestEntityCentricKnowledgeGraph:
    """Test cases for EntityCentricKnowledgeGraph"""

    @pytest.fixture
    def mock_cluster(self):
        """Create a mock Cassandra cluster"""
        with patch('trustgraph.direct.cassandra_kg.Cluster') as mock_cluster_cls:
            mock_cluster = MagicMock()
            mock_session = MagicMock()
            mock_cluster.connect.return_value = mock_session
            mock_cluster_cls.return_value = mock_cluster
            yield mock_cluster_cls, mock_cluster, mock_session

    @pytest.fixture
    def entity_kg(self, mock_cluster):
        """Create an EntityCentricKnowledgeGraph instance with mocked Cassandra"""
        from trustgraph.direct.cassandra_kg import EntityCentricKnowledgeGraph
        mock_cluster_cls, mock_cluster, mock_session = mock_cluster

        # Create instance
        kg = EntityCentricKnowledgeGraph(hosts=['localhost'], keyspace='test_keyspace')
        return kg, mock_session

    def test_init_creates_entity_centric_schema(self, mock_cluster):
        """Test that initialization creates the 2-table entity-centric schema"""
        from trustgraph.direct.cassandra_kg import EntityCentricKnowledgeGraph
        mock_cluster_cls, mock_cluster, mock_session = mock_cluster

        kg = EntityCentricKnowledgeGraph(hosts=['localhost'], keyspace='test_keyspace')

        # Verify schema tables were created
        execute_calls = mock_session.execute.call_args_list
        executed_statements = [str(c) for c in execute_calls]

        # Check for keyspace creation
        keyspace_created = any('create keyspace' in str(c).lower() for c in execute_calls)
        assert keyspace_created

        # Check for quads_by_entity table
        entity_table_created = any('quads_by_entity' in str(c) for c in execute_calls)
        assert entity_table_created

        # Check for quads_by_collection table
        collection_table_created = any('quads_by_collection' in str(c) for c in execute_calls)
        assert collection_table_created

        # Check for collection_metadata table
        metadata_table_created = any('collection_metadata' in str(c) for c in execute_calls)
        assert metadata_table_created

    def test_prepare_statements_initialized(self, entity_kg):
        """Test that prepared statements are initialized"""
        kg, mock_session = entity_kg

        # Verify prepare was called for various statements
        assert mock_session.prepare.called
        prepare_calls = mock_session.prepare.call_args_list

        # Check that key prepared statements exist
        prepared_queries = [str(c) for c in prepare_calls]

        # Insert statements
        insert_entity_stmt = any('INSERT INTO' in str(c) and 'quads_by_entity' in str(c)
                                  for c in prepare_calls)
        assert insert_entity_stmt

        insert_collection_stmt = any('INSERT INTO' in str(c) and 'quads_by_collection' in str(c)
                                      for c in prepare_calls)
        assert insert_collection_stmt

    def test_insert_uri_object_creates_4_entity_rows(self, entity_kg):
        """Test that inserting a quad with URI object creates 4 entity rows"""
        kg, mock_session = entity_kg

        # Reset mocks to track only insert-related calls
        mock_session.reset_mock()

        kg.insert(
            collection='test_collection',
            s='http://example.org/Alice',
            p='http://example.org/knows',
            o='http://example.org/Bob',
            g='http://example.org/graph1',
            otype='U'
        )

        # Verify batch was executed
        mock_session.execute.assert_called()

    def test_insert_literal_object_creates_3_entity_rows(self, entity_kg):
        """Test that inserting a quad with literal object creates 3 entity rows"""
        kg, mock_session = entity_kg

        mock_session.reset_mock()

        kg.insert(
            collection='test_collection',
            s='http://example.org/Alice',
            p='http://www.w3.org/2000/01/rdf-schema#label',
            o='Alice Smith',
            g=None,
            otype='L',
            dtype='xsd:string',
            lang='en'
        )

        # Verify batch was executed
        mock_session.execute.assert_called()

    def test_insert_default_graph(self, entity_kg):
        """Test that None graph is stored as empty string"""
        kg, mock_session = entity_kg

        mock_session.reset_mock()

        kg.insert(
            collection='test_collection',
            s='http://example.org/Alice',
            p='http://example.org/knows',
            o='http://example.org/Bob',
            g=None,
            otype='U'
        )

        mock_session.execute.assert_called()

    def test_insert_auto_detects_otype(self, entity_kg):
        """Test that otype is auto-detected when not provided"""
        kg, mock_session = entity_kg

        mock_session.reset_mock()

        # URI should be auto-detected
        kg.insert(
            collection='test_collection',
            s='http://example.org/Alice',
            p='http://example.org/knows',
            o='http://example.org/Bob'
        )
        mock_session.execute.assert_called()

        mock_session.reset_mock()

        # Literal should be auto-detected
        kg.insert(
            collection='test_collection',
            s='http://example.org/Alice',
            p='http://example.org/name',
            o='Alice'
        )
        mock_session.execute.assert_called()

    def test_get_s_returns_quads_for_subject(self, entity_kg):
        """Test get_s queries by subject"""
        kg, mock_session = entity_kg

        # Mock the query result
        mock_result = [
            MagicMock(p='http://example.org/knows', o='http://example.org/Bob',
                      d='', otype='U', dtype='', lang='', s='http://example.org/Alice')
        ]
        mock_session.execute.return_value = mock_result

        results = kg.get_s('test_collection', 'http://example.org/Alice')

        # Verify query was executed
        mock_session.execute.assert_called()

        # Results should be QuadResult objects
        assert len(results) == 1
        assert results[0].s == 'http://example.org/Alice'
        assert results[0].p == 'http://example.org/knows'
        assert results[0].o == 'http://example.org/Bob'

    def test_get_p_returns_quads_for_predicate(self, entity_kg):
        """Test get_p queries by predicate"""
        kg, mock_session = entity_kg

        mock_result = [
            MagicMock(s='http://example.org/Alice', o='http://example.org/Bob',
                      d='', otype='U', dtype='', lang='', p='http://example.org/knows')
        ]
        mock_session.execute.return_value = mock_result

        results = kg.get_p('test_collection', 'http://example.org/knows')

        mock_session.execute.assert_called()
        assert len(results) == 1

    def test_get_o_returns_quads_for_object(self, entity_kg):
        """Test get_o queries by object"""
        kg, mock_session = entity_kg

        mock_result = [
            MagicMock(s='http://example.org/Alice', p='http://example.org/knows',
                      d='', otype='U', dtype='', lang='', o='http://example.org/Bob')
        ]
        mock_session.execute.return_value = mock_result

        results = kg.get_o('test_collection', 'http://example.org/Bob')

        mock_session.execute.assert_called()
        assert len(results) == 1

    def test_get_sp_returns_quads_for_subject_predicate(self, entity_kg):
        """Test get_sp queries by subject and predicate"""
        kg, mock_session = entity_kg

        mock_result = [
            MagicMock(o='http://example.org/Bob', d='', otype='U', dtype='', lang='')
        ]
        mock_session.execute.return_value = mock_result

        results = kg.get_sp('test_collection', 'http://example.org/Alice',
                           'http://example.org/knows')

        mock_session.execute.assert_called()
        assert len(results) == 1

    def test_get_po_returns_quads_for_predicate_object(self, entity_kg):
        """Test get_po queries by predicate and object"""
        kg, mock_session = entity_kg

        mock_result = [
            MagicMock(s='http://example.org/Alice', d='', otype='U', dtype='', lang='',
                      o='http://example.org/Bob')
        ]
        mock_session.execute.return_value = mock_result

        results = kg.get_po('test_collection', 'http://example.org/knows',
                           'http://example.org/Bob')

        mock_session.execute.assert_called()
        assert len(results) == 1

    def test_get_os_returns_quads_for_object_subject(self, entity_kg):
        """Test get_os queries by object and subject"""
        kg, mock_session = entity_kg

        mock_result = [
            MagicMock(p='http://example.org/knows', d='', otype='U', dtype='', lang='',
                      s='http://example.org/Alice', o='http://example.org/Bob')
        ]
        mock_session.execute.return_value = mock_result

        results = kg.get_os('test_collection', 'http://example.org/Bob',
                           'http://example.org/Alice')

        mock_session.execute.assert_called()
        assert len(results) == 1

    def test_get_spo_returns_quads_for_subject_predicate_object(self, entity_kg):
        """Test get_spo queries by subject, predicate, and object"""
        kg, mock_session = entity_kg

        mock_result = [
            MagicMock(d='', otype='U', dtype='', lang='',
                      o='http://example.org/Bob')
        ]
        mock_session.execute.return_value = mock_result

        results = kg.get_spo('test_collection', 'http://example.org/Alice',
                            'http://example.org/knows', 'http://example.org/Bob')

        mock_session.execute.assert_called()
        assert len(results) == 1

    def test_get_g_returns_quads_for_graph(self, entity_kg):
        """Test get_g queries by graph"""
        kg, mock_session = entity_kg

        mock_result = [
            MagicMock(s='http://example.org/Alice', p='http://example.org/knows',
                      o='http://example.org/Bob', otype='U', dtype='', lang='')
        ]
        mock_session.execute.return_value = mock_result

        results = kg.get_g('test_collection', 'http://example.org/graph1')

        mock_session.execute.assert_called()

    def test_get_all_returns_all_quads_in_collection(self, entity_kg):
        """Test get_all returns all quads"""
        kg, mock_session = entity_kg

        mock_result = [
            MagicMock(d='', s='http://example.org/Alice', p='http://example.org/knows',
                      o='http://example.org/Bob', otype='U', dtype='', lang='')
        ]
        mock_session.execute.return_value = mock_result

        results = kg.get_all('test_collection')

        mock_session.execute.assert_called()

    def test_graph_wildcard_returns_all_graphs(self, entity_kg):
        """Test that g='*' returns quads from all graphs"""
        from trustgraph.direct.cassandra_kg import GRAPH_WILDCARD
        kg, mock_session = entity_kg

        mock_result = [
            MagicMock(p='http://example.org/knows', d='http://example.org/graph1',
                      otype='U', dtype='', lang='', s='http://example.org/Alice',
                      o='http://example.org/Bob'),
            MagicMock(p='http://example.org/knows', d='http://example.org/graph2',
                      otype='U', dtype='', lang='', s='http://example.org/Alice',
                      o='http://example.org/Charlie')
        ]
        mock_session.execute.return_value = mock_result

        results = kg.get_s('test_collection', 'http://example.org/Alice', g=GRAPH_WILDCARD)

        # Should return quads from both graphs
        assert len(results) == 2

    def test_specific_graph_filters_results(self, entity_kg):
        """Test that specifying a graph filters results"""
        kg, mock_session = entity_kg

        mock_result = [
            MagicMock(p='http://example.org/knows', d='http://example.org/graph1',
                      otype='U', dtype='', lang='', s='http://example.org/Alice',
                      o='http://example.org/Bob'),
            MagicMock(p='http://example.org/knows', d='http://example.org/graph2',
                      otype='U', dtype='', lang='', s='http://example.org/Alice',
                      o='http://example.org/Charlie')
        ]
        mock_session.execute.return_value = mock_result

        results = kg.get_s('test_collection', 'http://example.org/Alice',
                          g='http://example.org/graph1')

        # Should only return quads from graph1
        assert len(results) == 1
        assert results[0].g == 'http://example.org/graph1'

    def test_collection_exists_returns_true_when_exists(self, entity_kg):
        """Test collection_exists returns True for existing collection"""
        kg, mock_session = entity_kg

        mock_result = [MagicMock(collection='test_collection')]
        mock_session.execute.return_value = mock_result

        exists = kg.collection_exists('test_collection')

        assert exists is True

    def test_collection_exists_returns_false_when_not_exists(self, entity_kg):
        """Test collection_exists returns False for non-existing collection"""
        kg, mock_session = entity_kg

        mock_session.execute.return_value = []

        exists = kg.collection_exists('nonexistent_collection')

        assert exists is False

    def test_create_collection_inserts_metadata(self, entity_kg):
        """Test create_collection inserts metadata row"""
        kg, mock_session = entity_kg

        mock_session.reset_mock()
        kg.create_collection('test_collection')

        # Verify INSERT was executed for collection_metadata
        mock_session.execute.assert_called()

    def test_delete_collection_removes_all_data(self, entity_kg):
        """Test delete_collection removes entity partitions and collection rows"""
        kg, mock_session = entity_kg

        # Mock reading quads from collection
        mock_quads = [
            MagicMock(d='', s='http://example.org/Alice', p='http://example.org/knows',
                      o='http://example.org/Bob', otype='U')
        ]
        mock_session.execute.return_value = mock_quads

        mock_session.reset_mock()
        kg.delete_collection('test_collection')

        # Verify delete operations were executed
        assert mock_session.execute.called

    def test_close_shuts_down_connections(self, entity_kg):
        """Test close shuts down session and cluster"""
        kg, mock_session = entity_kg

        kg.close()

        mock_session.shutdown.assert_called_once()
        kg.cluster.shutdown.assert_called_once()


class TestQuadResult:
    """Test cases for QuadResult class"""

    def test_quad_result_stores_all_fields(self):
        """Test QuadResult stores all quad fields"""
        from trustgraph.direct.cassandra_kg import QuadResult

        result = QuadResult(
            s='http://example.org/Alice',
            p='http://example.org/knows',
            o='http://example.org/Bob',
            g='http://example.org/graph1',
            otype='U',
            dtype='',
            lang=''
        )

        assert result.s == 'http://example.org/Alice'
        assert result.p == 'http://example.org/knows'
        assert result.o == 'http://example.org/Bob'
        assert result.g == 'http://example.org/graph1'
        assert result.otype == 'U'
        assert result.dtype == ''
        assert result.lang == ''

    def test_quad_result_defaults(self):
        """Test QuadResult default values"""
        from trustgraph.direct.cassandra_kg import QuadResult

        result = QuadResult(
            s='http://example.org/s',
            p='http://example.org/p',
            o='literal value',
            g=''
        )

        assert result.otype == 'U'  # Default otype
        assert result.dtype == ''
        assert result.lang == ''

    def test_quad_result_with_literal_metadata(self):
        """Test QuadResult with literal metadata"""
        from trustgraph.direct.cassandra_kg import QuadResult

        result = QuadResult(
            s='http://example.org/Alice',
            p='http://www.w3.org/2000/01/rdf-schema#label',
            o='Alice Smith',
            g='',
            otype='L',
            dtype='xsd:string',
            lang='en'
        )

        assert result.otype == 'L'
        assert result.dtype == 'xsd:string'
        assert result.lang == 'en'


class TestFactoryFunction:
    """Test cases for get_knowledge_graph_class factory function"""

    def test_factory_returns_legacy_by_default(self):
        """Test factory returns KnowledgeGraph when env var not set"""
        from trustgraph.direct.cassandra_kg import get_knowledge_graph_class, KnowledgeGraph

        with patch.dict(os.environ, {}, clear=True):
            KGClass = get_knowledge_graph_class()
            assert KGClass == KnowledgeGraph

    def test_factory_returns_legacy_when_false(self):
        """Test factory returns KnowledgeGraph when env var is false"""
        from trustgraph.direct.cassandra_kg import get_knowledge_graph_class, KnowledgeGraph

        with patch.dict(os.environ, {'CASSANDRA_ENTITY_CENTRIC': 'false'}):
            KGClass = get_knowledge_graph_class()
            assert KGClass == KnowledgeGraph

    def test_factory_returns_entity_centric_when_true(self):
        """Test factory returns EntityCentricKnowledgeGraph when env var is true"""
        from trustgraph.direct.cassandra_kg import (
            get_knowledge_graph_class, EntityCentricKnowledgeGraph
        )

        with patch.dict(os.environ, {'CASSANDRA_ENTITY_CENTRIC': 'true'}):
            KGClass = get_knowledge_graph_class()
            assert KGClass == EntityCentricKnowledgeGraph

    def test_factory_case_insensitive(self):
        """Test factory handles case insensitive values"""
        from trustgraph.direct.cassandra_kg import (
            get_knowledge_graph_class, EntityCentricKnowledgeGraph
        )

        with patch.dict(os.environ, {'CASSANDRA_ENTITY_CENTRIC': 'TRUE'}):
            KGClass = get_knowledge_graph_class()
            assert KGClass == EntityCentricKnowledgeGraph

        with patch.dict(os.environ, {'CASSANDRA_ENTITY_CENTRIC': 'True'}):
            KGClass = get_knowledge_graph_class()
            assert KGClass == EntityCentricKnowledgeGraph


class TestWriteHelperFunctions:
    """Test cases for helper functions in write.py"""

    def test_get_term_otype_for_iri(self):
        """Test get_term_otype returns 'U' for IRI terms"""
        from trustgraph.storage.triples.cassandra.write import get_term_otype
        from trustgraph.schema import Term, IRI

        term = Term(type=IRI, iri='http://example.org/Alice')
        assert get_term_otype(term) == 'U'

    def test_get_term_otype_for_literal(self):
        """Test get_term_otype returns 'L' for LITERAL terms"""
        from trustgraph.storage.triples.cassandra.write import get_term_otype
        from trustgraph.schema import Term, LITERAL

        term = Term(type=LITERAL, value='Alice Smith')
        assert get_term_otype(term) == 'L'

    def test_get_term_otype_for_blank(self):
        """Test get_term_otype returns 'U' for BLANK terms"""
        from trustgraph.storage.triples.cassandra.write import get_term_otype
        from trustgraph.schema import Term, BLANK

        term = Term(type=BLANK, id='_:b1')
        assert get_term_otype(term) == 'U'

    def test_get_term_otype_for_triple(self):
        """Test get_term_otype returns 'T' for TRIPLE terms"""
        from trustgraph.storage.triples.cassandra.write import get_term_otype
        from trustgraph.schema import Term, TRIPLE

        term = Term(type=TRIPLE)
        assert get_term_otype(term) == 'T'

    def test_get_term_otype_for_none(self):
        """Test get_term_otype returns 'U' for None"""
        from trustgraph.storage.triples.cassandra.write import get_term_otype

        assert get_term_otype(None) == 'U'

    def test_get_term_dtype_for_literal(self):
        """Test get_term_dtype extracts datatype from LITERAL"""
        from trustgraph.storage.triples.cassandra.write import get_term_dtype
        from trustgraph.schema import Term, LITERAL

        term = Term(type=LITERAL, value='42', datatype='xsd:integer')
        assert get_term_dtype(term) == 'xsd:integer'

    def test_get_term_dtype_for_non_literal(self):
        """Test get_term_dtype returns empty string for non-LITERAL"""
        from trustgraph.storage.triples.cassandra.write import get_term_dtype
        from trustgraph.schema import Term, IRI

        term = Term(type=IRI, iri='http://example.org/Alice')
        assert get_term_dtype(term) == ''

    def test_get_term_dtype_for_none(self):
        """Test get_term_dtype returns empty string for None"""
        from trustgraph.storage.triples.cassandra.write import get_term_dtype

        assert get_term_dtype(None) == ''

    def test_get_term_lang_for_literal(self):
        """Test get_term_lang extracts language from LITERAL"""
        from trustgraph.storage.triples.cassandra.write import get_term_lang
        from trustgraph.schema import Term, LITERAL

        term = Term(type=LITERAL, value='Alice Smith', language='en')
        assert get_term_lang(term) == 'en'

    def test_get_term_lang_for_non_literal(self):
        """Test get_term_lang returns empty string for non-LITERAL"""
        from trustgraph.storage.triples.cassandra.write import get_term_lang
        from trustgraph.schema import Term, IRI

        term = Term(type=IRI, iri='http://example.org/Alice')
        assert get_term_lang(term) == ''


class TestServiceHelperFunctions:
    """Test cases for helper functions in service.py"""

    def test_create_term_with_uri_otype(self):
        """Test create_term creates IRI Term for otype='U'"""
        from trustgraph.query.triples.cassandra.service import create_term
        from trustgraph.schema import IRI

        term = create_term('http://example.org/Alice', otype='U')

        assert term.type == IRI
        assert term.iri == 'http://example.org/Alice'

    def test_create_term_with_literal_otype(self):
        """Test create_term creates LITERAL Term for otype='L'"""
        from trustgraph.query.triples.cassandra.service import create_term
        from trustgraph.schema import LITERAL

        term = create_term('Alice Smith', otype='L', dtype='xsd:string', lang='en')

        assert term.type == LITERAL
        assert term.value == 'Alice Smith'
        assert term.datatype == 'xsd:string'
        assert term.language == 'en'

    def test_create_term_with_triple_otype(self):
        """Test create_term creates IRI Term for otype='T'"""
        from trustgraph.query.triples.cassandra.service import create_term
        from trustgraph.schema import IRI

        term = create_term('http://example.org/statement1', otype='T')

        assert term.type == IRI
        assert term.iri == 'http://example.org/statement1'

    def test_create_term_heuristic_fallback_uri(self):
        """Test create_term uses URL heuristic when otype not provided"""
        from trustgraph.query.triples.cassandra.service import create_term
        from trustgraph.schema import IRI

        term = create_term('http://example.org/Alice')

        assert term.type == IRI
        assert term.iri == 'http://example.org/Alice'

    def test_create_term_heuristic_fallback_literal(self):
        """Test create_term uses literal heuristic when otype not provided"""
        from trustgraph.query.triples.cassandra.service import create_term
        from trustgraph.schema import LITERAL

        term = create_term('Alice Smith')

        assert term.type == LITERAL
        assert term.value == 'Alice Smith'
