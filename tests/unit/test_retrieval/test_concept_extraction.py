"""
Tests for the concept extraction service.

Covers the Processor.extract() method: concept parsing, empty-query
handling, and fallback to raw query when the LLM returns nothing useful.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from trustgraph.retrieval.concept_extraction.service import Processor
from trustgraph.schema import ConceptExtractionRequest, ConceptExtractionResponse
from trustgraph.base import PromptResult


def _make_processor():
    """Create a Processor without triggering FlowProcessor.__init__."""
    proc = Processor.__new__(Processor)
    return proc


def _make_flow(prompt_text):
    """Build a mock flow whose prompt-request client returns *prompt_text*."""
    prompt_client = AsyncMock()
    prompt_client.prompt.return_value = PromptResult(
        response_type="text", text=prompt_text,
    )

    def flow_fn(name):
        if name == "prompt-request":
            return prompt_client
        raise ValueError(f"unexpected flow name: {name}")

    flow = MagicMock(side_effect=flow_fn)
    flow.prompt_client = prompt_client
    return flow, prompt_client


class TestConceptExtraction:
    """Test Processor.extract() method."""

    @pytest.mark.asyncio
    async def test_extract_parses_newline_separated_concepts(self):
        proc = _make_processor()
        flow, prompt_client = _make_flow(
            "quantum computing\nphysics\nmathematics\n"
        )

        request = ConceptExtractionRequest(query="What is quantum computing?")
        response = await proc.extract("ws-1", request, flow)

        assert isinstance(response, ConceptExtractionResponse)
        assert response.concepts == [
            "quantum computing", "physics", "mathematics",
        ]
        prompt_client.prompt.assert_called_once_with(
            "extract-concepts",
            variables={"query": "What is quantum computing?"},
        )

    @pytest.mark.asyncio
    async def test_extract_falls_back_to_raw_query_on_empty_response(self):
        proc = _make_processor()
        flow, _ = _make_flow("")

        request = ConceptExtractionRequest(query="test query")
        response = await proc.extract("ws-1", request, flow)

        assert response.concepts == ["test query"]

    @pytest.mark.asyncio
    async def test_extract_empty_query_returns_empty_concepts(self):
        proc = _make_processor()
        flow, prompt_client = _make_flow("should not be called")

        request = ConceptExtractionRequest(query="")
        response = await proc.extract("ws-1", request, flow)

        assert response.concepts == []
        prompt_client.prompt.assert_not_called()

    @pytest.mark.asyncio
    async def test_extract_strips_whitespace_lines(self):
        proc = _make_processor()
        flow, _ = _make_flow("  concept one  \n\n  concept two  \n  \n")

        request = ConceptExtractionRequest(query="test")
        response = await proc.extract("ws-1", request, flow)

        assert response.concepts == ["concept one", "concept two"]

    @pytest.mark.asyncio
    async def test_extract_whitespace_only_response_falls_back(self):
        proc = _make_processor()
        flow, _ = _make_flow("   \n  \n  ")

        request = ConceptExtractionRequest(query="fallback query")
        response = await proc.extract("ws-1", request, flow)

        assert response.concepts == ["fallback query"]
