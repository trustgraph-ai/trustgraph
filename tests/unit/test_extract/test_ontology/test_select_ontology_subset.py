"""
Unit tests for the refactored extract processor's _select_ontology_subset
method. This is the key change from step 2: the processor now segments
the chunk text and makes per-segment requests to the ontology service,
then merges the results.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

from trustgraph.extract.kg.ontology.extract import Processor
from trustgraph.schema import OntologyRequest, OntologyResponse, Error


@dataclass
class FakeSegment:
    text: str
    type: str = "sentence"
    position: int = 0
    parent_sentence: Optional[str] = None
    metadata: Dict[str, Any] = None


def _make_response(
    ontology_id="test", namespace="http://example.org/",
    classes=None, obj_props=None, dt_props=None, error=None,
):
    return OntologyResponse(
        operation="subset",
        ontology_id=ontology_id,
        classes=classes or {},
        object_properties=obj_props or {},
        datatype_properties=dt_props or {},
        namespace=namespace,
        error=error,
    )


@pytest.fixture
def processor():
    p = object.__new__(Processor)
    p.top_k = 10
    p.similarity_threshold = 0.3
    p.text_processor = MagicMock()
    return p


class TestSelectOntologySubset:

    @pytest.mark.asyncio
    async def test_single_segment_returns_its_results(self, processor):
        processor.text_processor.process_chunk.return_value = [
            FakeSegment(text="Dogs are animals")
        ]

        ontology_client = AsyncMock()
        ontology_client.request = AsyncMock(return_value=_make_response(
            classes={
                "Dog": json.dumps({"uri": "http://example.org/Dog"}),
                "Animal": json.dumps({"uri": "http://example.org/Animal"}),
            },
        ))

        flow = MagicMock()
        flow.return_value = ontology_client

        result = await processor._select_ontology_subset(flow, "Dogs are animals")

        assert "Dog" in result.classes
        assert "Animal" in result.classes
        assert result.ontology_id == "test"

    @pytest.mark.asyncio
    async def test_merges_classes_from_multiple_segments(self, processor):
        processor.text_processor.process_chunk.return_value = [
            FakeSegment(text="Dogs are loyal"),
            FakeSegment(text="Cats are independent"),
        ]

        responses = [
            _make_response(classes={
                "Dog": json.dumps({"uri": "http://example.org/Dog"}),
            }),
            _make_response(classes={
                "Cat": json.dumps({"uri": "http://example.org/Cat"}),
            }),
        ]

        ontology_client = AsyncMock()
        ontology_client.request = AsyncMock(side_effect=responses)

        flow = MagicMock()
        flow.return_value = ontology_client

        result = await processor._select_ontology_subset(flow, "chunk text")

        assert "Dog" in result.classes
        assert "Cat" in result.classes

    @pytest.mark.asyncio
    async def test_merges_all_property_types(self, processor):
        processor.text_processor.process_chunk.return_value = [
            FakeSegment(text="seg1"),
            FakeSegment(text="seg2"),
        ]

        responses = [
            _make_response(
                obj_props={"owns": json.dumps({"uri": "http://example.org/owns"})},
            ),
            _make_response(
                dt_props={"name": json.dumps({"uri": "http://example.org/name"})},
            ),
        ]

        ontology_client = AsyncMock()
        ontology_client.request = AsyncMock(side_effect=responses)

        flow = MagicMock()
        flow.return_value = ontology_client

        result = await processor._select_ontology_subset(flow, "chunk")

        assert "owns" in result.object_properties
        assert "name" in result.datatype_properties

    @pytest.mark.asyncio
    async def test_first_nonempty_ontology_id_wins(self, processor):
        processor.text_processor.process_chunk.return_value = [
            FakeSegment(text="seg1"),
            FakeSegment(text="seg2"),
        ]

        responses = [
            _make_response(ontology_id="first"),
            _make_response(ontology_id="second"),
        ]

        ontology_client = AsyncMock()
        ontology_client.request = AsyncMock(side_effect=responses)

        flow = MagicMock()
        flow.return_value = ontology_client

        result = await processor._select_ontology_subset(flow, "chunk")

        assert result.ontology_id == "first"

    @pytest.mark.asyncio
    async def test_skips_empty_ontology_id(self, processor):
        processor.text_processor.process_chunk.return_value = [
            FakeSegment(text="seg1"),
            FakeSegment(text="seg2"),
        ]

        responses = [
            _make_response(ontology_id=""),
            _make_response(ontology_id="real"),
        ]

        ontology_client = AsyncMock()
        ontology_client.request = AsyncMock(side_effect=responses)

        flow = MagicMock()
        flow.return_value = ontology_client

        result = await processor._select_ontology_subset(flow, "chunk")

        assert result.ontology_id == "real"

    @pytest.mark.asyncio
    async def test_duplicate_keys_keep_first(self, processor):
        processor.text_processor.process_chunk.return_value = [
            FakeSegment(text="seg1"),
            FakeSegment(text="seg2"),
        ]

        responses = [
            _make_response(classes={
                "Dog": json.dumps({"uri": "http://example.org/Dog", "comment": "first"}),
            }),
            _make_response(classes={
                "Dog": json.dumps({"uri": "http://example.org/Dog", "comment": "second"}),
            }),
        ]

        ontology_client = AsyncMock()
        ontology_client.request = AsyncMock(side_effect=responses)

        flow = MagicMock()
        flow.return_value = ontology_client

        result = await processor._select_ontology_subset(flow, "chunk")

        assert result.classes["Dog"]["comment"] == "first"

    @pytest.mark.asyncio
    async def test_error_response_skipped(self, processor):
        processor.text_processor.process_chunk.return_value = [
            FakeSegment(text="seg1"),
            FakeSegment(text="seg2"),
        ]

        responses = [
            _make_response(
                error=Error(type="no-ontology", message="not loaded"),
            ),
            _make_response(classes={
                "Dog": json.dumps({"uri": "http://example.org/Dog"}),
            }),
        ]

        ontology_client = AsyncMock()
        ontology_client.request = AsyncMock(side_effect=responses)

        flow = MagicMock()
        flow.return_value = ontology_client

        result = await processor._select_ontology_subset(flow, "chunk")

        assert "Dog" in result.classes

    @pytest.mark.asyncio
    async def test_all_errors_returns_empty_subset(self, processor):
        processor.text_processor.process_chunk.return_value = [
            FakeSegment(text="seg1"),
        ]

        ontology_client = AsyncMock()
        ontology_client.request = AsyncMock(return_value=_make_response(
            error=Error(type="no-ontology", message="not loaded"),
        ))

        flow = MagicMock()
        flow.return_value = ontology_client

        result = await processor._select_ontology_subset(flow, "chunk")

        assert result.classes == {}
        assert result.object_properties == {}
        assert result.datatype_properties == {}
        assert result.ontology_id == ""

    @pytest.mark.asyncio
    async def test_no_segments_returns_empty_subset(self, processor):
        processor.text_processor.process_chunk.return_value = []

        flow = MagicMock()

        result = await processor._select_ontology_subset(flow, "")

        assert result.classes == {}
        assert result.ontology_id == ""

    @pytest.mark.asyncio
    async def test_passes_top_k_and_threshold(self, processor):
        processor.top_k = 5
        processor.similarity_threshold = 0.7
        processor.text_processor.process_chunk.return_value = [
            FakeSegment(text="test"),
        ]

        ontology_client = AsyncMock()
        ontology_client.request = AsyncMock(return_value=_make_response())

        flow = MagicMock()
        flow.return_value = ontology_client

        await processor._select_ontology_subset(flow, "test")

        call_args = ontology_client.request.call_args[0][0]
        assert call_args.top_k == 5
        assert call_args.similarity_threshold == 0.7
        assert call_args.operation == "subset"

    @pytest.mark.asyncio
    async def test_json_string_values_decoded(self, processor):
        processor.text_processor.process_chunk.return_value = [
            FakeSegment(text="test"),
        ]

        ontology_client = AsyncMock()
        ontology_client.request = AsyncMock(return_value=_make_response(
            classes={
                "Dog": json.dumps({"uri": "http://example.org/Dog", "comment": "A dog"}),
            },
        ))

        flow = MagicMock()
        flow.return_value = ontology_client

        result = await processor._select_ontology_subset(flow, "test")

        assert isinstance(result.classes["Dog"], dict)
        assert result.classes["Dog"]["uri"] == "http://example.org/Dog"

    @pytest.mark.asyncio
    async def test_dict_values_passed_through(self, processor):
        processor.text_processor.process_chunk.return_value = [
            FakeSegment(text="test"),
        ]

        ontology_client = AsyncMock()
        ontology_client.request = AsyncMock(return_value=_make_response(
            classes={
                "Dog": {"uri": "http://example.org/Dog"},
            },
        ))

        flow = MagicMock()
        flow.return_value = ontology_client

        result = await processor._select_ontology_subset(flow, "test")

        assert isinstance(result.classes["Dog"], dict)
        assert result.classes["Dog"]["uri"] == "http://example.org/Dog"
