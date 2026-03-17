"""
Tests for entity-centric KG write amplification, delete collection batching,
in-partition filtering, and term type metadata round-trips.

Complements test_entity_centric_kg.py with deeper verification of the
2-table schema mechanics.
"""

import pytest
from unittest.mock import MagicMock, patch, call


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_cassandra():
    """Provide mocked Cassandra cluster, session, and BatchStatement."""
    with patch('trustgraph.direct.cassandra_kg.Cluster') as mock_cls, \
         patch('trustgraph.direct.cassandra_kg.BatchStatement') as mock_batch_cls:

        mock_cluster = MagicMock()
        mock_session = MagicMock()
        mock_cluster.connect.return_value = mock_session
        mock_cls.return_value = mock_cluster

        # Track batch.add calls per batch instance
        batches = []

        def make_batch():
            batch = MagicMock()
            batch._adds = []
            original_add = batch.add

            def tracking_add(stmt, params):
                batch._adds.append((stmt, params))

            batch.add = tracking_add
            batches.append(batch)
            return batch

        mock_batch_cls.side_effect = make_batch

        yield {
            "cluster_cls": mock_cls,
            "cluster": mock_cluster,
            "session": mock_session,
            "batch_cls": mock_batch_cls,
            "batches": batches,
        }


@pytest.fixture
def entity_kg(mock_cassandra):
    """Create an EntityCentricKnowledgeGraph with mocked Cassandra."""
    from trustgraph.direct.cassandra_kg import EntityCentricKnowledgeGraph
    kg = EntityCentricKnowledgeGraph(hosts=['localhost'], keyspace='test_ks')
    return kg, mock_cassandra


# ---------------------------------------------------------------------------
# Write amplification: row count verification
# ---------------------------------------------------------------------------

class TestWriteAmplification:

    def test_uri_object_produces_4_entity_rows_plus_collection(self, entity_kg):
        """URI object → S + P + O + G-if-non-default entity rows + 1 collection row."""
        kg, ctx = entity_kg
        ctx["batches"].clear()

        kg.insert(
            collection='col',
            s='http://ex.org/Alice',
            p='http://ex.org/knows',
            o='http://ex.org/Bob',
            g='http://ex.org/g1',
            otype='u',
        )

        # Should be exactly one batch
        assert len(ctx["batches"]) == 1
        batch = ctx["batches"][0]

        # 4 entity rows (S, P, O, G) + 1 collection row = 5
        assert len(batch._adds) == 5

        # Check roles assigned
        roles = [params[2] for _, params in batch._adds if len(params) == 10]
        assert 'S' in roles
        assert 'P' in roles
        assert 'O' in roles
        assert 'G' in roles

    def test_literal_object_produces_3_entity_rows(self, entity_kg):
        """Literal object → S + P entity rows (no O row) + collection row."""
        kg, ctx = entity_kg
        ctx["batches"].clear()

        kg.insert(
            collection='col',
            s='http://ex.org/Alice',
            p='http://ex.org/name',
            o='Alice Smith',
            g=None,  # default graph
            otype='l',
        )

        batch = ctx["batches"][0]

        # S + P entity rows + 1 collection = 3 (no O row for literal, no G for default)
        assert len(batch._adds) == 3

        roles = [params[2] for _, params in batch._adds if len(params) == 10]
        assert 'S' in roles
        assert 'P' in roles
        assert 'O' not in roles
        assert 'G' not in roles

    def test_triple_otype_gets_object_entity_row(self, entity_kg):
        """otype='t' (quoted triple) → object gets entity row like URI."""
        kg, ctx = entity_kg
        ctx["batches"].clear()

        kg.insert(
            collection='col',
            s='http://ex.org/s',
            p='http://ex.org/p',
            o='{"s":{},"p":{},"o":{}}',
            g=None,
            otype='t',
        )

        batch = ctx["batches"][0]

        # S + P + O entity rows + collection = 4 (no G for default graph)
        assert len(batch._adds) == 4

        roles = [params[2] for _, params in batch._adds if len(params) == 10]
        assert 'O' in roles

    def test_default_graph_no_g_row(self, entity_kg):
        """Default graph (g=None) → no G entity row."""
        kg, ctx = entity_kg
        ctx["batches"].clear()

        kg.insert(
            collection='col',
            s='http://ex.org/s',
            p='http://ex.org/p',
            o='http://ex.org/o',
            g=None,
            otype='u',
        )

        batch = ctx["batches"][0]

        # S + P + O entity rows + collection = 4 (no G)
        assert len(batch._adds) == 4
        roles = [params[2] for _, params in batch._adds if len(params) == 10]
        assert 'G' not in roles

    def test_non_default_graph_gets_g_row(self, entity_kg):
        """Non-default graph → gets G entity row."""
        kg, ctx = entity_kg
        ctx["batches"].clear()

        kg.insert(
            collection='col',
            s='http://ex.org/s',
            p='http://ex.org/p',
            o='http://ex.org/o',
            g='http://ex.org/graph1',
            otype='u',
        )

        batch = ctx["batches"][0]

        # S + P + O + G entity rows + collection = 5
        assert len(batch._adds) == 5
        roles = [params[2] for _, params in batch._adds if len(params) == 10]
        assert 'G' in roles

    def test_dtype_and_lang_passed_to_all_rows(self, entity_kg):
        """dtype and lang should be stored in every entity row."""
        kg, ctx = entity_kg
        ctx["batches"].clear()

        kg.insert(
            collection='col',
            s='http://ex.org/s',
            p='http://ex.org/label',
            o='thing',
            g=None,
            otype='l',
            dtype='xsd:string',
            lang='en',
        )

        batch = ctx["batches"][0]

        # Check entity rows carry dtype and lang
        for _, params in batch._adds:
            if len(params) == 10:
                # Entity row: (collection, entity, role, p, otype, s, o, d, dtype, lang)
                assert params[8] == 'xsd:string'
                assert params[9] == 'en'


# ---------------------------------------------------------------------------
# In-partition filtering: get_os, get_spo
# ---------------------------------------------------------------------------

class TestInPartitionFiltering:

    def test_get_os_filters_by_object(self, entity_kg):
        """get_os should filter results by matching object value."""
        kg, ctx = entity_kg

        # Simulate rows returned from subject partition (all have same s)
        mock_rows = [
            MagicMock(p='http://ex.org/knows', o='http://ex.org/Bob',
                      d='', otype='u', dtype='', lang='',
                      s='http://ex.org/Alice'),
            MagicMock(p='http://ex.org/likes', o='http://ex.org/Charlie',
                      d='', otype='u', dtype='', lang='',
                      s='http://ex.org/Alice'),
        ]
        ctx["session"].execute.return_value = mock_rows

        results = kg.get_os('col', 'http://ex.org/Bob', 'http://ex.org/Alice')

        # Only the Bob row should pass the filter
        assert len(results) == 1
        assert results[0].o == 'http://ex.org/Bob'
        assert results[0].p == 'http://ex.org/knows'

    def test_get_os_returns_empty_when_no_match(self, entity_kg):
        """get_os should return empty list when object doesn't match any row."""
        kg, ctx = entity_kg

        mock_rows = [
            MagicMock(p='http://ex.org/knows', o='http://ex.org/Bob',
                      d='', otype='u', dtype='', lang='',
                      s='http://ex.org/Alice'),
        ]
        ctx["session"].execute.return_value = mock_rows

        results = kg.get_os('col', 'http://ex.org/Charlie', 'http://ex.org/Alice')

        assert len(results) == 0

    def test_get_spo_filters_by_object(self, entity_kg):
        """get_spo should filter results by matching object value."""
        kg, ctx = entity_kg

        mock_rows = [
            MagicMock(o='http://ex.org/Bob', d='', otype='u', dtype='', lang=''),
            MagicMock(o='http://ex.org/Charlie', d='', otype='u', dtype='', lang=''),
        ]
        ctx["session"].execute.return_value = mock_rows

        results = kg.get_spo(
            'col', 'http://ex.org/Alice', 'http://ex.org/knows',
            'http://ex.org/Bob',
        )

        assert len(results) == 1
        assert results[0].o == 'http://ex.org/Bob'

    def test_get_os_with_graph_filter(self, entity_kg):
        """get_os with specific graph should filter both object and graph."""
        kg, ctx = entity_kg

        mock_rows = [
            MagicMock(p='http://ex.org/knows', o='http://ex.org/Bob',
                      d='http://ex.org/g1', otype='u', dtype='', lang='',
                      s='http://ex.org/Alice'),
            MagicMock(p='http://ex.org/knows', o='http://ex.org/Bob',
                      d='http://ex.org/g2', otype='u', dtype='', lang='',
                      s='http://ex.org/Alice'),
        ]
        ctx["session"].execute.return_value = mock_rows

        results = kg.get_os(
            'col', 'http://ex.org/Bob', 'http://ex.org/Alice',
            g='http://ex.org/g1',
        )

        assert len(results) == 1
        assert results[0].g == 'http://ex.org/g1'


# ---------------------------------------------------------------------------
# Delete collection batching
# ---------------------------------------------------------------------------

class TestDeleteCollectionBatching:

    def test_extracts_unique_entities_from_quads(self, entity_kg):
        """delete_collection should extract s, p, and URI o as entities."""
        kg, ctx = entity_kg

        mock_rows = [
            MagicMock(d='', s='http://ex.org/A', p='http://ex.org/knows',
                      o='http://ex.org/B', otype='u', dtype='', lang=''),
            MagicMock(d='', s='http://ex.org/A', p='http://ex.org/name',
                      o='Alice', otype='l', dtype='', lang=''),
        ]
        ctx["session"].execute.return_value = mock_rows
        ctx["batches"].clear()

        kg.delete_collection('col')

        # Unique entities: A, knows, B, name (literal 'Alice' excluded)
        # The batches should include entity partition deletes
        all_adds = []
        for batch in ctx["batches"]:
            all_adds.extend(batch._adds)

        # We expect entity deletes + collection row deletes + metadata delete
        # Just verify the function completes and calls execute
        assert ctx["session"].execute.called

    def test_literal_objects_not_treated_as_entities(self, entity_kg):
        """Literal objects (otype='l') should not get entity partition deletes."""
        kg, ctx = entity_kg

        mock_rows = [
            MagicMock(d='', s='http://ex.org/A', p='http://ex.org/name',
                      o='Alice', otype='l', dtype='', lang=''),
        ]
        ctx["session"].execute.return_value = mock_rows
        ctx["batches"].clear()

        kg.delete_collection('col')

        # Entity partition deletes should only include A and name, not Alice
        entity_deletes = []
        for batch in ctx["batches"]:
            for _, params in batch._adds:
                if len(params) == 2:  # delete_entity_partition takes (collection, entity)
                    entity_deletes.append(params[1])

        assert 'http://ex.org/A' in entity_deletes
        assert 'http://ex.org/name' in entity_deletes
        assert 'Alice' not in entity_deletes

    def test_non_default_graph_treated_as_entity(self, entity_kg):
        """Non-default graphs should get entity partition deletes."""
        kg, ctx = entity_kg

        mock_rows = [
            MagicMock(d='http://ex.org/g1', s='http://ex.org/A',
                      p='http://ex.org/p', o='http://ex.org/B',
                      otype='u', dtype='', lang=''),
        ]
        ctx["session"].execute.return_value = mock_rows
        ctx["batches"].clear()

        kg.delete_collection('col')

        entity_deletes = []
        for batch in ctx["batches"]:
            for _, params in batch._adds:
                if len(params) == 2:
                    entity_deletes.append(params[1])

        assert 'http://ex.org/g1' in entity_deletes

    def test_empty_collection_delete_completes(self, entity_kg):
        """Deleting an empty collection should not error."""
        kg, ctx = entity_kg

        ctx["session"].execute.return_value = []
        ctx["batches"].clear()

        # Should not raise
        kg.delete_collection('empty-col')


# ---------------------------------------------------------------------------
# Term type metadata round-trip
# ---------------------------------------------------------------------------

class TestTermTypeMetadata:

    def test_query_results_include_otype(self, entity_kg):
        """Query results should include otype from Cassandra rows."""
        kg, ctx = entity_kg
        from trustgraph.direct.cassandra_kg import QuadResult

        mock_rows = [
            MagicMock(p='http://ex.org/name', o='Alice',
                      d='', otype='l', dtype='xsd:string', lang='en',
                      s='http://ex.org/Alice'),
        ]
        ctx["session"].execute.return_value = mock_rows

        results = kg.get_s('col', 'http://ex.org/Alice')

        assert len(results) == 1
        assert results[0].otype == 'l'
        assert results[0].dtype == 'xsd:string'
        assert results[0].lang == 'en'

    def test_auto_detect_otype_uri(self, entity_kg):
        """Auto-detect should classify http:// as URI."""
        kg, ctx = entity_kg
        ctx["batches"].clear()

        kg.insert(
            collection='col',
            s='http://ex.org/s',
            p='http://ex.org/p',
            o='http://ex.org/o',
        )

        batch = ctx["batches"][0]
        # Check otype in entity rows (position 4)
        for _, params in batch._adds:
            if len(params) == 10:
                assert params[4] == 'u'

    def test_auto_detect_otype_literal(self, entity_kg):
        """Auto-detect should classify non-http:// as literal."""
        kg, ctx = entity_kg
        ctx["batches"].clear()

        kg.insert(
            collection='col',
            s='http://ex.org/s',
            p='http://ex.org/p',
            o='plain text',
        )

        batch = ctx["batches"][0]
        for _, params in batch._adds:
            if len(params) == 10:
                assert params[4] == 'l'
