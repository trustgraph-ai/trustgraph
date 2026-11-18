"""
Tests for guided graph traversal features:
- Mutual exclusivity validation (grounding_seeds vs graph_seeds)
- Translator round-trip (encode/decode of new GraphRagQuery fields)

Feature tests for grounding seeds, graph seeds, language filtering,
traversal instructions, and direction-aware reranker text have moved
to test_knowledge_retrieval_traversal.py where the TraversalEngine
now implements those features.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock

from trustgraph.schema import GraphRagQuery, TraversalStep
from trustgraph.messaging.translators.retrieval import GraphRagRequestTranslator


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
