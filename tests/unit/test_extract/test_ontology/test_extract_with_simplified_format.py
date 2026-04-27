"""
Unit tests for extract_with_simplified_format.

Regression guard for the bug where the extractor read
``result.object`` (singular, used for response_type="json") instead of
``result.objects`` (plural, used for response_type="jsonl"). The
extract-with-ontologies prompt is JSONL, so reading the wrong field
silently dropped every extraction and left the knowledge graph
populated only by ontology schema + document provenance.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from trustgraph.extract.kg.ontology.extract import Processor
from trustgraph.extract.kg.ontology.ontology_selector import OntologySubset
from trustgraph.base import PromptResult


@pytest.fixture
def extractor():
    """Create a Processor instance without running its heavy __init__.

    Matches the pattern used in test_prompt_and_extraction.py: only
    the attributes the code under test touches need to be set.
    """
    ex = object.__new__(Processor)
    ex.URI_PREFIXES = {
        "rdf:":  "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "rdfs:": "http://www.w3.org/2000/01/rdf-schema#",
        "owl:":  "http://www.w3.org/2002/07/owl#",
        "xsd:":  "http://www.w3.org/2001/XMLSchema#",
    }
    return ex


@pytest.fixture
def food_subset():
    """A minimal food ontology subset the extracted entities reference."""
    return OntologySubset(
        ontology_id="food",
        classes={
            "Recipe": {
                "uri": "http://purl.org/ontology/fo/Recipe",
                "type": "owl:Class",
                "labels": [{"value": "Recipe", "lang": "en-gb"}],
                "comment": "A Recipe.",
            },
            "Food": {
                "uri": "http://purl.org/ontology/fo/Food",
                "type": "owl:Class",
                "labels": [{"value": "Food", "lang": "en-gb"}],
                "comment": "A Food.",
            },
        },
        object_properties={
            "ingredients": {
                "uri": "http://purl.org/ontology/fo/ingredients",
                "type": "owl:ObjectProperty",
                "labels": [{"value": "ingredients", "lang": "en-gb"}],
                "comment": "Relates a recipe to its ingredients.",
                "domain": "Recipe",
                "range": "Food",
            },
        },
        datatype_properties={},
        metadata={
            "name": "Food Ontology",
            "namespace": "http://purl.org/ontology/fo/",
        },
    )


def _flow_with_prompt_result(prompt_result):
    """Build the ``flow(name)`` callable the extractor invokes.

    ``extract_with_simplified_format`` calls
    ``flow("prompt-request").prompt(...)`` — so we need ``flow`` to be
    callable, return an object whose ``.prompt`` is an AsyncMock that
    resolves to ``prompt_result``.
    """
    prompt_service = MagicMock()
    prompt_service.prompt = AsyncMock(return_value=prompt_result)

    def flow(name):
        assert name == "prompt-request", (
            f"extractor should only invoke flow('prompt-request'), "
            f"got {name!r}"
        )
        return prompt_service

    return flow, prompt_service.prompt


class TestReadsObjectsForJsonlPrompt:
    """extract-with-ontologies is a JSONL prompt; the extractor must
    read ``result.objects``, not ``result.object``."""

    async def test_populated_objects_produces_triples(
            self, extractor, food_subset,
    ):
        """Happy path: PromptResult with populated .objects -> non-empty
        triples list."""

        prompt_result = PromptResult(
            response_type="jsonl",
            objects=[
                {"type": "entity", "entity": "Cornish Pasty",
                 "entity_type": "Recipe"},
                {"type": "entity", "entity": "beef",
                 "entity_type": "Food"},
                {"type": "relationship",
                 "subject": "Cornish Pasty", "subject_type": "Recipe",
                 "relation": "ingredients",
                 "object": "beef", "object_type": "Food"},
            ],
        )

        flow, prompt_mock = _flow_with_prompt_result(prompt_result)

        triples = await extractor.extract_with_simplified_format(
            flow, "some chunk", food_subset, {"text": "some chunk"},
        )

        prompt_mock.assert_awaited_once()
        assert triples, (
            "extract_with_simplified_format returned no triples; if "
            "this fails, the extractor is probably reading .object "
            "instead of .objects again"
        )

    async def test_none_objects_returns_empty_without_crashing(
            self, extractor, food_subset,
    ):
        """The exact shape that hit production on v2.3: the extractor
        was reading ``.object`` for a JSONL prompt, which returned
        ``None`` and tripped the parser's 'Unexpected response type'
        path.  With the fix we read ``.objects``; if that's also
        ``None`` we must still return ``[]`` cleanly, not crash."""

        prompt_result = PromptResult(
            response_type="jsonl",
            objects=None,
        )

        flow, _ = _flow_with_prompt_result(prompt_result)

        triples = await extractor.extract_with_simplified_format(
            flow, "chunk", food_subset, {"text": "chunk"},
        )

        assert triples == []

    async def test_empty_objects_returns_empty(
            self, extractor, food_subset,
    ):
        """Valid JSONL response with zero entries should yield zero
        triples, not raise."""

        prompt_result = PromptResult(
            response_type="jsonl",
            objects=[],
        )

        flow, _ = _flow_with_prompt_result(prompt_result)

        triples = await extractor.extract_with_simplified_format(
            flow, "chunk", food_subset, {"text": "chunk"},
        )

        assert triples == []

    async def test_ignores_object_field_for_jsonl_prompt(
            self, extractor, food_subset,
    ):
        """If ``.object`` is somehow set but ``.objects`` is None, the
        extractor must not silently fall back to ``.object``.  This
        guards against a well-meaning regression that "helpfully"
        re-adds fallback fields.

        The extractor should read only ``.objects`` for this prompt;
        when that is None we expect the empty-result path.
        """

        prompt_result = PromptResult(
            response_type="json",
            object={"not": "the field we should be reading"},
            objects=None,
        )

        flow, _ = _flow_with_prompt_result(prompt_result)

        triples = await extractor.extract_with_simplified_format(
            flow, "chunk", food_subset, {"text": "chunk"},
        )

        assert triples == [], (
            "Extractor fell back to .object for a JSONL prompt — "
            "this is the regression shape we are trying to prevent"
        )
