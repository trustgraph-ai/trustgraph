"""
Tests for guided graph traversal features:
- Grounding seeds (bypass LLM concept extraction)
- Graph seeds (bypass grounding and entity lookup)
- Language filtering
- Traversal instructions (per-hop type/relationship/graph restrictions)
- Mutual exclusivity validation
- Translator round-trip
"""

import pytest
from unittest.mock import MagicMock, AsyncMock

from trustgraph.retrieval.graph_rag.graph_rag import GraphRag, Query
from trustgraph.schema import GraphRagQuery, TraversalStep
from trustgraph.messaging.translators.retrieval import GraphRagRequestTranslator
from trustgraph.base import PromptResult


class TestGroundingSeeds:
    """Test grounding seeds bypass LLM concept extraction."""

    @pytest.mark.asyncio
    async def test_grounding_seeds_skip_llm_extraction(self):
        mock_rag = MagicMock()
        mock_prompt_client = AsyncMock()
        mock_embeddings_client = AsyncMock()
        mock_graph_embeddings_client = AsyncMock()
        mock_rag.prompt_client = mock_prompt_client
        mock_rag.embeddings_client = mock_embeddings_client
        mock_rag.graph_embeddings_client = mock_graph_embeddings_client

        mock_embeddings_client.embed.return_value = [[0.1, 0.2]]
        mock_graph_embeddings_client.query.return_value = []

        query = Query(
            rag=mock_rag,
            collection="test",
            verbose=False,
            grounding_seeds=["graphrag", "retrieval"],
        )

        entities, concepts = await query.get_entities("some query")

        mock_prompt_client.prompt.assert_not_called()
        assert concepts == ["graphrag", "retrieval"]
        mock_embeddings_client.embed.assert_called_once_with(
            ["graphrag", "retrieval"]
        )

    @pytest.mark.asyncio
    async def test_grounding_seeds_empty_uses_llm(self):
        mock_rag = MagicMock()
        mock_prompt_client = AsyncMock()
        mock_embeddings_client = AsyncMock()
        mock_graph_embeddings_client = AsyncMock()
        mock_rag.prompt_client = mock_prompt_client
        mock_rag.embeddings_client = mock_embeddings_client
        mock_rag.graph_embeddings_client = mock_graph_embeddings_client

        mock_prompt_client.prompt.return_value = PromptResult(
            response_type="text", text="concept1\n"
        )
        mock_embeddings_client.embed.return_value = [[0.1]]
        mock_graph_embeddings_client.query.return_value = []

        query = Query(
            rag=mock_rag,
            collection="test",
            verbose=False,
            grounding_seeds=[],
        )

        _, concepts = await query.get_entities("test query")

        mock_prompt_client.prompt.assert_called_once()
        assert concepts == ["concept1"]


class TestGraphSeeds:
    """Test graph seeds bypass grounding and entity lookup."""

    @pytest.mark.asyncio
    async def test_graph_seeds_bypass_all_lookup(self):
        mock_rag = MagicMock()
        mock_prompt_client = AsyncMock()
        mock_embeddings_client = AsyncMock()
        mock_graph_embeddings_client = AsyncMock()
        mock_rag.prompt_client = mock_prompt_client
        mock_rag.embeddings_client = mock_embeddings_client
        mock_rag.graph_embeddings_client = mock_graph_embeddings_client

        seeds = [
            "http://example.org/Person/Jane",
            "http://example.org/Person/John",
        ]

        query = Query(
            rag=mock_rag,
            collection="test",
            verbose=False,
            graph_seeds=seeds,
        )

        entities, concepts = await query.get_entities("some query")

        mock_prompt_client.prompt.assert_not_called()
        mock_embeddings_client.embed.assert_not_called()
        mock_graph_embeddings_client.query.assert_not_called()
        assert entities == seeds
        assert concepts == ["some query"]

    @pytest.mark.asyncio
    async def test_graph_seeds_empty_uses_normal_flow(self):
        mock_rag = MagicMock()
        mock_prompt_client = AsyncMock()
        mock_embeddings_client = AsyncMock()
        mock_graph_embeddings_client = AsyncMock()
        mock_rag.prompt_client = mock_prompt_client
        mock_rag.embeddings_client = mock_embeddings_client
        mock_rag.graph_embeddings_client = mock_graph_embeddings_client

        mock_prompt_client.prompt.return_value = PromptResult(
            response_type="text", text="concept\n"
        )
        mock_embeddings_client.embed.return_value = [[0.1]]
        mock_graph_embeddings_client.query.return_value = []

        query = Query(
            rag=mock_rag,
            collection="test",
            verbose=False,
            graph_seeds=[],
        )

        entities, concepts = await query.get_entities("test query")

        mock_prompt_client.prompt.assert_called_once()
        mock_embeddings_client.embed.assert_called_once()


class TestSeedMutualExclusivity:
    """Test that grounding_seeds and graph_seeds cannot both be set."""

    @pytest.mark.asyncio
    async def test_both_seeds_raises_error(self):
        from trustgraph.retrieval.graph_rag.rag import Processor
        from unittest.mock import patch

        processor = Processor(
            taskgroup=MagicMock(),
            id="test-processor",
        )

        msg = MagicMock()
        msg.value.return_value = GraphRagQuery(
            query="test",
            collection="default",
            streaming=False,
            grounding_seeds=["concept1"],
            graph_seeds=["http://example.org/entity"],
        )
        msg.properties.return_value = {"id": "test-id"}

        consumer = MagicMock()
        flow = MagicMock()
        mock_response_producer = AsyncMock()
        flow.side_effect = lambda name: mock_response_producer

        with patch('trustgraph.retrieval.graph_rag.rag.GraphRag'):
            await processor.on_request(msg, consumer, flow)

        sent = mock_response_producer.send.call_args[0][0]
        assert sent.error is not None
        assert "mutually exclusive" in sent.error.message


class TestLanguageFiltering:
    """Test language tag filtering on triples."""

    def _make_query(self, languages):
        mock_rag = MagicMock()
        return Query(
            rag=mock_rag,
            collection="test",
            verbose=False,
            languages=languages,
        )

    def _make_triple(self, s_lang=None, o_lang=None, s_is_iri=False,
                     o_is_iri=False):
        triple = MagicMock()

        if s_is_iri:
            triple.s = MagicMock(spec=[])
        else:
            triple.s = MagicMock()
            triple.s.language = s_lang
            triple.s.value = "some value"

        if o_is_iri:
            triple.o = MagicMock(spec=[])
        else:
            triple.o = MagicMock()
            triple.o.language = o_lang
            triple.o.value = "some value"

        return triple

    def test_no_filter_passes_everything(self):
        q = self._make_query([])
        triple = self._make_triple(o_lang="de")
        assert q._matches_language(triple) is True

    def test_matching_language_passes(self):
        q = self._make_query(["en"])
        triple = self._make_triple(o_lang="en")
        assert q._matches_language(triple) is True

    def test_non_matching_language_rejected(self):
        q = self._make_query(["en"])
        triple = self._make_triple(o_lang="de")
        assert q._matches_language(triple) is False

    def test_empty_string_matches_no_language_tag(self):
        q = self._make_query([""])
        triple = self._make_triple(o_lang=None)
        assert q._matches_language(triple) is True

    def test_multiple_languages(self):
        q = self._make_query(["en", "fr"])
        assert q._matches_language(self._make_triple(o_lang="en")) is True
        assert q._matches_language(self._make_triple(o_lang="fr")) is True
        assert q._matches_language(self._make_triple(o_lang="de")) is False

    def test_iri_only_triple_passes_through(self):
        q = self._make_query(["en"])
        triple = self._make_triple(s_is_iri=True, o_is_iri=True)
        assert q._matches_language(triple) is True

    def test_mixed_iri_and_matching_literal(self):
        q = self._make_query(["en"])
        triple = self._make_triple(s_is_iri=True, o_lang="en")
        assert q._matches_language(triple) is True

    def test_mixed_iri_and_non_matching_literal(self):
        q = self._make_query(["en"])
        triple = self._make_triple(s_is_iri=True, o_lang="de")
        assert q._matches_language(triple) is False


class TestTraversalInstructionsRelationship:
    """Test per-hop relationship restrictions in hop_and_filter."""

    @pytest.mark.asyncio
    async def test_relationship_restriction_filters_edges(self):
        """Verify that hop_and_filter drops edges whose predicate is not
        in the traversal instruction's relationship whitelist."""
        from unittest.mock import patch

        mock_rag = MagicMock()
        mock_triples_client = AsyncMock()
        mock_reranker_client = AsyncMock()
        mock_rag.triples_client = mock_triples_client
        mock_rag.reranker_client = mock_reranker_client
        mock_rag.label_cache = MagicMock()
        mock_rag.label_cache.get.return_value = None
        mock_triples_client.query.return_value = []

        allowed_pred = "http://example.org/worksFor"
        blocked_pred = "http://example.org/knows"

        triple_allowed = MagicMock()
        triple_allowed.s = "entity1"
        triple_allowed.p = allowed_pred
        triple_allowed.o = "org1"

        triple_blocked = MagicMock()
        triple_blocked.s = "entity1"
        triple_blocked.p = blocked_pred
        triple_blocked.o = "entity2"

        instructions = [
            TraversalStep(),
            TraversalStep(relationships=[allowed_pred]),
        ]

        query = Query(
            rag=mock_rag,
            collection="test",
            verbose=False,
            triple_limit=10,
            traversal_instructions=instructions,
        )

        # Patch execute_batch_triple_queries to return controlled
        # (triple, direction) pairs, bypassing the async mock complexity
        async def fake_batch(entities, limit, graphs=None):
            return [
                (triple_allowed, Query.FROM_S),
                (triple_blocked, Query.FROM_S),
            ]

        with patch.object(query, "execute_batch_triple_queries",
                          side_effect=fake_batch):
            await query.hop_and_filter(["entity1"], ["concept"])

        # Only triple_allowed should survive the relationship filter.
        # Its predicate is an IRI with no label, so the IRI check
        # may also discard it — but the blocked triple must never
        # appear.
        if mock_reranker_client.rerank.called:
            docs = mock_reranker_client.rerank.call_args.kwargs["documents"]
            for doc in docs:
                assert blocked_pred not in doc["text"]
                assert "knows" not in doc["text"]


class TestTraversalInstructionsType:
    """Test per-hop type restrictions."""

    @pytest.mark.asyncio
    async def test_initial_type_restriction_filters_seeds(self):
        mock_rag = MagicMock()
        mock_triples_client = AsyncMock()
        mock_reranker_client = AsyncMock()
        mock_rag.triples_client = mock_triples_client
        mock_rag.reranker_client = mock_reranker_client
        mock_rag.label_cache = MagicMock()
        mock_rag.label_cache.get.return_value = None

        person_type = "http://example.org/Person"

        type_triple = MagicMock()
        type_triple.o = person_type

        async def mock_query(s=None, p=None, o=None, limit=20,
                             collection="", g="", user_context=None):
            if s == "entity_person" and p is not None:
                return [type_triple]
            if s == "entity_org" and p is not None:
                other_type = MagicMock()
                other_type.o = "http://example.org/Organisation"
                return [other_type]
            return []

        mock_triples_client.query.side_effect = mock_query
        mock_triples_client.query_stream.return_value = []

        instructions = [
            TraversalStep(types=[person_type]),
        ]

        query = Query(
            rag=mock_rag,
            collection="test",
            verbose=False,
            triple_limit=10,
            traversal_instructions=instructions,
        )

        await query.hop_and_filter(
            ["entity_person", "entity_org"], ["concept"],
        )

        query_stream_calls = mock_triples_client.query_stream.call_args_list
        queried_entities = set()
        for call in query_stream_calls:
            for val in [call.kwargs.get("s"), call.kwargs.get("o")]:
                if val is not None:
                    queried_entities.add(val)

        assert "entity_person" in queried_entities
        assert "entity_org" not in queried_entities


class TestTraversalInstructionsGraph:
    """Test named graph restrictions in triple queries."""

    @pytest.mark.asyncio
    async def test_graph_restriction_queries_specific_graphs(self):
        mock_rag = MagicMock()
        mock_triples_client = AsyncMock()
        mock_reranker_client = AsyncMock()
        mock_rag.triples_client = mock_triples_client
        mock_rag.reranker_client = mock_reranker_client
        mock_rag.label_cache = MagicMock()
        mock_rag.label_cache.get.return_value = None

        mock_triples_client.query_stream.return_value = []

        graph_uri = "urn:graph:knowledge"
        instructions = [
            TraversalStep(),
            TraversalStep(graphs=[graph_uri]),
        ]

        query = Query(
            rag=mock_rag,
            collection="test",
            verbose=False,
            triple_limit=10,
            traversal_instructions=instructions,
        )

        await query.hop_and_filter(["entity1"], ["concept"])

        for call in mock_triples_client.query_stream.call_args_list:
            assert call.kwargs["g"] == graph_uri

    @pytest.mark.asyncio
    async def test_no_graph_restriction_uses_empty_string(self):
        mock_rag = MagicMock()
        mock_triples_client = AsyncMock()
        mock_reranker_client = AsyncMock()
        mock_rag.triples_client = mock_triples_client
        mock_rag.reranker_client = mock_reranker_client
        mock_rag.label_cache = MagicMock()
        mock_rag.label_cache.get.return_value = None

        mock_triples_client.query_stream.return_value = []

        query = Query(
            rag=mock_rag,
            collection="test",
            verbose=False,
            triple_limit=10,
        )

        await query.hop_and_filter(["entity1"], ["concept"])

        for call in mock_triples_client.query_stream.call_args_list:
            assert call.kwargs["g"] == ""


class TestTranslatorRoundTrip:
    """Test encoding/decoding of new fields through the translator."""

    def test_decode_with_new_fields(self):
        translator = GraphRagRequestTranslator()
        data = {
            "query": "test",
            "grounding-seeds": ["concept1", "concept2"],
            "graph-seeds": [],
            "languages": ["en", ""],
            "traversal-instructions": [
                {"types": ["http://example.org/Person"]},
                {
                    "relationships": ["http://example.org/worksFor"],
                    "types": ["http://example.org/Org"],
                    "graphs": ["urn:graph:knowledge"],
                },
            ],
        }

        result = translator.decode(data)

        assert result.grounding_seeds == ["concept1", "concept2"]
        assert result.graph_seeds == []
        assert result.languages == ["en", ""]
        assert len(result.traversal_instructions) == 2
        assert result.traversal_instructions[0].types == [
            "http://example.org/Person"
        ]
        assert result.traversal_instructions[1].relationships == [
            "http://example.org/worksFor"
        ]
        assert result.traversal_instructions[1].graphs == [
            "urn:graph:knowledge"
        ]

    def test_decode_without_new_fields(self):
        translator = GraphRagRequestTranslator()
        data = {"query": "test"}

        result = translator.decode(data)

        assert result.grounding_seeds == []
        assert result.graph_seeds == []
        assert result.languages == []
        assert result.traversal_instructions == []

    def test_encode_with_new_fields(self):
        translator = GraphRagRequestTranslator()
        query = GraphRagQuery(
            query="test",
            collection="default",
            grounding_seeds=["c1"],
            languages=["en"],
            traversal_instructions=[
                TraversalStep(types=["http://example.org/Person"]),
                TraversalStep(
                    relationships=["http://example.org/worksFor"],
                    graphs=["urn:graph:knowledge"],
                ),
            ],
        )

        encoded = translator.encode(query)

        assert encoded["grounding-seeds"] == ["c1"]
        assert encoded["languages"] == ["en"]
        assert "graph-seeds" not in encoded
        assert len(encoded["traversal-instructions"]) == 2
        assert encoded["traversal-instructions"][0] == {
            "types": ["http://example.org/Person"]
        }
        assert encoded["traversal-instructions"][1] == {
            "relationships": ["http://example.org/worksFor"],
            "graphs": ["urn:graph:knowledge"],
        }

    def test_encode_without_new_fields(self):
        translator = GraphRagRequestTranslator()
        query = GraphRagQuery(query="test", collection="default")

        encoded = translator.encode(query)

        assert "grounding-seeds" not in encoded
        assert "graph-seeds" not in encoded
        assert "languages" not in encoded
        assert "traversal-instructions" not in encoded

    def test_round_trip(self):
        translator = GraphRagRequestTranslator()
        original = GraphRagQuery(
            query="test query",
            collection="my-collection",
            entity_limit=100,
            grounding_seeds=["a", "b"],
            languages=["en", "fr", ""],
            traversal_instructions=[
                TraversalStep(types=["http://example.org/T1"]),
                TraversalStep(
                    relationships=["http://example.org/r1"],
                    types=["http://example.org/T2"],
                    graphs=["urn:graph:g1"],
                ),
            ],
        )

        encoded = translator.encode(original)
        decoded = translator.decode(encoded)

        assert decoded.query == original.query
        assert decoded.collection == original.collection
        assert decoded.entity_limit == original.entity_limit
        assert decoded.grounding_seeds == original.grounding_seeds
        assert decoded.languages == original.languages
        assert len(decoded.traversal_instructions) == 2
        assert (
            decoded.traversal_instructions[0].types
            == original.traversal_instructions[0].types
        )
        assert (
            decoded.traversal_instructions[1].relationships
            == original.traversal_instructions[1].relationships
        )
        assert (
            decoded.traversal_instructions[1].graphs
            == original.traversal_instructions[1].graphs
        )


class TestQueryInitializationNewFields:
    """Test that Query stores the new guided traversal fields."""

    def test_defaults(self):
        q = Query(rag=MagicMock(), collection="test", verbose=False)
        assert q.grounding_seeds == []
        assert q.graph_seeds == []
        assert q.languages == []
        assert q.traversal_instructions == []

    def test_custom_values(self):
        seeds = ["http://example.org/e1"]
        langs = ["en"]
        instructions = [TraversalStep(types=["http://example.org/T"])]

        q = Query(
            rag=MagicMock(),
            collection="test",
            verbose=False,
            graph_seeds=seeds,
            languages=langs,
            traversal_instructions=instructions,
        )

        assert q.graph_seeds == seeds
        assert q.languages == langs
        assert q.traversal_instructions == instructions
