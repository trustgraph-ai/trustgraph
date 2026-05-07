"""
Tests for the ontology-driven SPARQL generator.

Covers regression for issue #870: an empty / whitespace-only LLM response
must not raise IndexError when the keyword-startswith guard is bypassed.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

# The trustgraph.query.ontology package __init__ chains imports that can
# fail outside the deployed FlowProcessor environment, so the suite is
# skipped at collection if the module cannot be imported.
sparql_generator = pytest.importorskip(
    "trustgraph.query.ontology.sparql_generator",
)
question_analyzer = pytest.importorskip(
    "trustgraph.query.ontology.question_analyzer",
)
ontology_matcher = pytest.importorskip(
    "trustgraph.query.ontology.ontology_matcher",
)

SPARQLGenerator = sparql_generator.SPARQLGenerator
SPARQLQuery = sparql_generator.SPARQLQuery
QuestionComponents = question_analyzer.QuestionComponents
QuestionType = question_analyzer.QuestionType
QueryOntologySubset = ontology_matcher.QueryOntologySubset


def _make_question_components():
    return QuestionComponents(
        original_question="dummy",
        question_type=QuestionType.RETRIEVAL,
        entities=[],
        relationships=[],
        constraints=[],
        aggregations=[],
        expected_answer_type="entity",
        keywords=[],
    )


def _make_ontology_subset():
    return QueryOntologySubset(
        ontology_id="test",
        classes={},
        object_properties={},
        datatype_properties={},
        metadata={"namespace": "http://example.org/"},
    )


class TestGenerateWithLlm:
    """Regression tests for _generate_with_llm parsing safety."""

    @pytest.mark.asyncio
    async def test_valid_select_response_returns_query(self):
        """Sanity: a well-formed LLM response yields a SPARQLQuery."""
        prompt_service = MagicMock()
        prompt_service.generate_sparql = AsyncMock(return_value={
            "query": "SELECT ?s WHERE { ?s ?p ?o }",
            "explanation": "test",
        })
        generator = SPARQLGenerator(prompt_service=prompt_service)

        result = await generator._generate_with_llm(
            _make_question_components(), _make_ontology_subset(),
        )

        assert isinstance(result, SPARQLQuery)
        assert result.query_type == "SELECT"

    @pytest.mark.asyncio
    async def test_empty_query_does_not_raise_index_error(self):
        """An empty 'query' string in the LLM response must not crash.

        Regression for issue #870: query.split()[0] raised IndexError
        when the keyword-startswith guard was bypassed. Parsing now
        returns None instead of crashing.
        """
        prompt_service = MagicMock()
        prompt_service.generate_sparql = AsyncMock(return_value={
            "query": "",
            "explanation": "empty",
        })
        generator = SPARQLGenerator(prompt_service=prompt_service)

        result = await generator._generate_with_llm(
            _make_question_components(), _make_ontology_subset(),
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_whitespace_only_query_does_not_raise_index_error(self):
        """A whitespace-only 'query' string must not crash.

        After .strip() the value becomes empty; the keyword-startswith
        guard rejects it, but the parsing code stays safe even if the
        guard is ever weakened. Verifies the empty-parts defence added
        for issue #870.
        """
        prompt_service = MagicMock()
        prompt_service.generate_sparql = AsyncMock(return_value={
            "query": "   \n\t  ",
            "explanation": "whitespace",
        })
        generator = SPARQLGenerator(prompt_service=prompt_service)

        result = await generator._generate_with_llm(
            _make_question_components(), _make_ontology_subset(),
        )

        assert result is None
