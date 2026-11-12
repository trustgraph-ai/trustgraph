"""
Unit tests for the NL-to-SPARQL translation service.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from dataclasses import dataclass

from trustgraph.retrieval.nl_sparql.service import Processor
from trustgraph.schema import (
    OntologyRequest, OntologyResponse, Error,
    QuestionToSparqlRequest, IRI, LITERAL, Term,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ontology_response(
    classes=None, obj_props=None, dt_props=None,
    namespace="http://example.org/", ontology_id="test",
    error=None,
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


SAMPLE_CLASSES = {
    "Player": json.dumps({
        "uri": "http://example.org/Player",
        "comment": "A game player",
    }),
    "Action": json.dumps({
        "uri": "http://example.org/Action",
        "comment": "A possible action",
        "subclass_of": "Choice",
    }),
}

SAMPLE_OBJ_PROPS = {
    "hasAction": json.dumps({
        "uri": "http://example.org/hasAction",
        "comment": "Links to an action",
        "domain": "Player",
        "range": "Action",
    }),
}

SAMPLE_DT_PROPS = {
    "label": json.dumps({
        "uri": "http://example.org/label",
        "domain": "Action",
        "range": "string",
    }),
}


@pytest.fixture
def processor():
    p = object.__new__(Processor)
    p.entity_limit = 5
    return p


# ---------------------------------------------------------------------------
# _ontology_classes_for_prompt
# ---------------------------------------------------------------------------

class TestOntologyClassesForPrompt:

    def test_basic_class(self, processor):
        ontology = _make_ontology_response(classes=SAMPLE_CLASSES)
        result = processor._ontology_classes_for_prompt(ontology)

        by_id = {e["id"]: e for e in result}
        assert "Player" in by_id
        assert by_id["Player"]["uri"] == "http://example.org/Player"
        assert by_id["Player"]["description"] == "A game player"

    def test_includes_subclass_of(self, processor):
        ontology = _make_ontology_response(classes=SAMPLE_CLASSES)
        result = processor._ontology_classes_for_prompt(ontology)

        by_id = {e["id"]: e for e in result}
        assert by_id["Action"]["subclass_of"] == "Choice"

    def test_omits_empty_optional_fields(self, processor):
        ontology = _make_ontology_response(classes={
            "X": json.dumps({"uri": "http://example.org/X"}),
        })
        result = processor._ontology_classes_for_prompt(ontology)

        assert len(result) == 1
        assert "description" not in result[0]
        assert "subclass_of" not in result[0]

    def test_handles_dict_values(self, processor):
        ontology = _make_ontology_response(classes={
            "X": {"uri": "http://example.org/X", "comment": "a thing"},
        })
        result = processor._ontology_classes_for_prompt(ontology)

        assert result[0]["description"] == "a thing"


class TestOntologyObjPropsForPrompt:

    def test_includes_domain_and_range(self, processor):
        ontology = _make_ontology_response(obj_props=SAMPLE_OBJ_PROPS)
        result = processor._ontology_obj_props_for_prompt(ontology)

        assert len(result) == 1
        assert result[0]["domain"] == "Player"
        assert result[0]["range"] == "Action"

    def test_omits_empty_optional_fields(self, processor):
        ontology = _make_ontology_response(obj_props={
            "p": json.dumps({"uri": "http://example.org/p"}),
        })
        result = processor._ontology_obj_props_for_prompt(ontology)

        assert "domain" not in result[0]
        assert "range" not in result[0]
        assert "description" not in result[0]


class TestOntologyDtPropsForPrompt:

    def test_basic(self, processor):
        ontology = _make_ontology_response(dt_props=SAMPLE_DT_PROPS)
        result = processor._ontology_dt_props_for_prompt(ontology)

        assert len(result) == 1
        assert result[0]["id"] == "label"
        assert result[0]["domain"] == "Action"
        assert result[0]["range"] == "string"


# ---------------------------------------------------------------------------
# _resolve_class_uri
# ---------------------------------------------------------------------------

class TestResolveClassUri:

    def test_resolves_json_string(self, processor):
        ontology = _make_ontology_response(classes=SAMPLE_CLASSES)
        assert processor._resolve_class_uri(
            ontology, "Player"
        ) == "http://example.org/Player"

    def test_resolves_dict_value(self, processor):
        ontology = _make_ontology_response(classes={
            "Player": {"uri": "http://example.org/Player"},
        })
        assert processor._resolve_class_uri(
            ontology, "Player"
        ) == "http://example.org/Player"

    def test_unknown_class_returns_id(self, processor):
        ontology = _make_ontology_response(classes={})
        assert processor._resolve_class_uri(ontology, "Unknown") == "Unknown"

    def test_no_uri_in_definition_returns_id(self, processor):
        ontology = _make_ontology_response(classes={
            "X": json.dumps({"comment": "no uri"}),
        })
        assert processor._resolve_class_uri(ontology, "X") == "X"


# ---------------------------------------------------------------------------
# _get_ontology_subset
# ---------------------------------------------------------------------------

class TestGetOntologySubset:

    @pytest.mark.asyncio
    async def test_returns_response_on_success(self, processor):
        ontology_client = AsyncMock()
        ontology_client.request = AsyncMock(
            return_value=_make_ontology_response(classes=SAMPLE_CLASSES)
        )

        flow = MagicMock()
        flow.return_value = ontology_client

        result = await processor._get_ontology_subset(flow, "some question")

        assert result is not None
        assert "Player" in result.classes

    @pytest.mark.asyncio
    async def test_returns_none_on_error(self, processor):
        ontology_client = AsyncMock()
        ontology_client.request = AsyncMock(
            return_value=_make_ontology_response(
                error=Error(type="fail", message="boom"),
            )
        )

        flow = MagicMock()
        flow.return_value = ontology_client

        result = await processor._get_ontology_subset(flow, "question")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_empty_subset(self, processor):
        ontology_client = AsyncMock()
        ontology_client.request = AsyncMock(
            return_value=_make_ontology_response()
        )

        flow = MagicMock()
        flow.return_value = ontology_client

        result = await processor._get_ontology_subset(flow, "question")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_exception(self, processor):
        ontology_client = AsyncMock()
        ontology_client.request = AsyncMock(
            side_effect=RuntimeError("connection lost")
        )

        flow = MagicMock()
        flow.return_value = ontology_client

        result = await processor._get_ontology_subset(flow, "question")
        assert result is None


# ---------------------------------------------------------------------------
# _extract_entities
# ---------------------------------------------------------------------------

class TestExtractEntities:

    @pytest.mark.asyncio
    async def test_returns_extracted_entities(self, processor):
        prompt_result = MagicMock()
        prompt_result.object = {
            "entities": [
                {"mention": "Farage", "type": "Player"},
                {"mention": "resign", "type": "Action"},
            ]
        }

        prompt_client = AsyncMock()
        prompt_client.prompt = AsyncMock(return_value=prompt_result)

        flow = MagicMock()
        flow.return_value = prompt_client

        ontology = _make_ontology_response(classes=SAMPLE_CLASSES)
        result = await processor._extract_entities(
            flow, "What can Farage do?", ontology
        )

        assert len(result) == 2
        assert result[0]["mention"] == "Farage"

    @pytest.mark.asyncio
    async def test_filters_invalid_entities(self, processor):
        prompt_result = MagicMock()
        prompt_result.object = {
            "entities": [
                {"mention": "Farage", "type": "Player"},
                "not a dict",
                {"no_mention_key": True},
            ]
        }

        prompt_client = AsyncMock()
        prompt_client.prompt = AsyncMock(return_value=prompt_result)

        flow = MagicMock()
        flow.return_value = prompt_client

        ontology = _make_ontology_response(classes=SAMPLE_CLASSES)
        result = await processor._extract_entities(
            flow, "question", ontology
        )

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_returns_empty_on_none_object(self, processor):
        prompt_result = MagicMock()
        prompt_result.object = None

        prompt_client = AsyncMock()
        prompt_client.prompt = AsyncMock(return_value=prompt_result)

        flow = MagicMock()
        flow.return_value = prompt_client

        ontology = _make_ontology_response(classes=SAMPLE_CLASSES)
        result = await processor._extract_entities(
            flow, "question", ontology
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_returns_empty_on_exception(self, processor):
        prompt_client = AsyncMock()
        prompt_client.prompt = AsyncMock(side_effect=RuntimeError("boom"))

        flow = MagicMock()
        flow.return_value = prompt_client

        ontology = _make_ontology_response(classes=SAMPLE_CLASSES)
        result = await processor._extract_entities(
            flow, "question", ontology
        )

        assert result == []


# ---------------------------------------------------------------------------
# _resolve_entities
# ---------------------------------------------------------------------------

@dataclass
class FakeGraphMatch:
    entity: Term
    score: float


class TestResolveEntities:

    @pytest.mark.asyncio
    async def test_resolves_entity_to_uri(self, processor):
        embeddings_client = AsyncMock()
        embeddings_client.embed = AsyncMock(
            return_value=[[0.1, 0.2, 0.3]]
        )

        graph_client = AsyncMock()
        graph_client.query = AsyncMock(return_value=[
            FakeGraphMatch(
                entity=Term(type=IRI, iri="http://example.org/farage"),
                score=0.87,
            )
        ])

        flow = MagicMock()
        flow.side_effect = lambda name: {
            "embeddings-request": embeddings_client,
            "graph-embeddings-request": graph_client,
        }[name]

        entities = [{"mention": "Farage", "type": "Player"}]
        ontology = _make_ontology_response(classes=SAMPLE_CLASSES)

        result = await processor._resolve_entities(
            flow, entities, "default", ontology
        )

        assert len(result) == 1
        assert result[0].mention == "Farage"
        assert result[0].uri == "http://example.org/farage"
        assert result[0].rdf_type == "Player"
        assert result[0].score == 0.87

    @pytest.mark.asyncio
    async def test_resolves_class_id_to_full_uri(self, processor):
        embeddings_client = AsyncMock()
        embeddings_client.embed = AsyncMock(
            return_value=[[0.1, 0.2, 0.3]]
        )

        graph_client = AsyncMock()
        graph_client.query = AsyncMock(return_value=[
            FakeGraphMatch(
                entity=Term(type=IRI, iri="http://example.org/farage"),
                score=0.9,
            )
        ])

        flow = MagicMock()
        flow.side_effect = lambda name: {
            "embeddings-request": embeddings_client,
            "graph-embeddings-request": graph_client,
        }[name]

        entities = [{"mention": "Farage", "type": "Player"}]
        ontology = _make_ontology_response(classes=SAMPLE_CLASSES)

        await processor._resolve_entities(
            flow, entities, "default", ontology
        )

        call_kwargs = graph_client.query.call_args[1]
        assert call_kwargs["rdf_type"] == "http://example.org/Player"

    @pytest.mark.asyncio
    async def test_skips_empty_mention(self, processor):
        embeddings_client = AsyncMock()
        graph_client = AsyncMock()

        flow = MagicMock()
        flow.side_effect = lambda name: {
            "embeddings-request": embeddings_client,
            "graph-embeddings-request": graph_client,
        }[name]

        entities = [{"mention": "", "type": "Player"}]
        ontology = _make_ontology_response(classes=SAMPLE_CLASSES)

        result = await processor._resolve_entities(
            flow, entities, "default", ontology
        )

        assert result == []
        embeddings_client.embed.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_on_empty_vectors(self, processor):
        embeddings_client = AsyncMock()
        embeddings_client.embed = AsyncMock(return_value=[[]])

        graph_client = AsyncMock()

        flow = MagicMock()
        flow.side_effect = lambda name: {
            "embeddings-request": embeddings_client,
            "graph-embeddings-request": graph_client,
        }[name]

        entities = [{"mention": "Farage", "type": "Player"}]
        ontology = _make_ontology_response(classes=SAMPLE_CLASSES)

        result = await processor._resolve_entities(
            flow, entities, "default", ontology
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_skips_on_no_matches(self, processor):
        embeddings_client = AsyncMock()
        embeddings_client.embed = AsyncMock(
            return_value=[[0.1, 0.2, 0.3]]
        )

        graph_client = AsyncMock()
        graph_client.query = AsyncMock(return_value=[])

        flow = MagicMock()
        flow.side_effect = lambda name: {
            "embeddings-request": embeddings_client,
            "graph-embeddings-request": graph_client,
        }[name]

        entities = [{"mention": "Farage", "type": "Player"}]
        ontology = _make_ontology_response(classes=SAMPLE_CLASSES)

        result = await processor._resolve_entities(
            flow, entities, "default", ontology
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_continues_on_per_entity_error(self, processor):
        embeddings_client = AsyncMock()
        embeddings_client.embed = AsyncMock(
            side_effect=[RuntimeError("boom"), [[0.1, 0.2]]]
        )

        graph_client = AsyncMock()
        graph_client.query = AsyncMock(return_value=[
            FakeGraphMatch(
                entity=Term(type=IRI, iri="http://example.org/x"),
                score=0.8,
            )
        ])

        flow = MagicMock()
        flow.side_effect = lambda name: {
            "embeddings-request": embeddings_client,
            "graph-embeddings-request": graph_client,
        }[name]

        entities = [
            {"mention": "Bad", "type": "Player"},
            {"mention": "Good", "type": "Action"},
        ]
        ontology = _make_ontology_response(classes=SAMPLE_CLASSES)

        result = await processor._resolve_entities(
            flow, entities, "default", ontology
        )

        assert len(result) == 1
        assert result[0].mention == "Good"


# ---------------------------------------------------------------------------
# _generate_sparql
# ---------------------------------------------------------------------------

class TestGenerateSparql:

    @pytest.mark.asyncio
    async def test_returns_sparql_text(self, processor):
        prompt_result = MagicMock()
        prompt_result.text = "SELECT ?x WHERE { ?x a :Player }"

        prompt_client = AsyncMock()
        prompt_client.prompt = AsyncMock(return_value=prompt_result)

        flow = MagicMock()
        flow.return_value = prompt_client

        ontology = _make_ontology_response(
            classes=SAMPLE_CLASSES,
            obj_props=SAMPLE_OBJ_PROPS,
            dt_props=SAMPLE_DT_PROPS,
        )

        result = await processor._generate_sparql(
            flow, "Who are the players?", ontology, [], 10
        )

        assert "SELECT" in result

    @pytest.mark.asyncio
    async def test_strips_markdown_fences(self, processor):
        prompt_result = MagicMock()
        prompt_result.text = "```sparql\nSELECT ?x WHERE { ?x a :Player }\n```"

        prompt_client = AsyncMock()
        prompt_client.prompt = AsyncMock(return_value=prompt_result)

        flow = MagicMock()
        flow.return_value = prompt_client

        ontology = _make_ontology_response(classes=SAMPLE_CLASSES)

        result = await processor._generate_sparql(
            flow, "question", ontology, [], 10
        )

        assert not result.startswith("```")
        assert not result.endswith("```")
        assert "SELECT" in result

    @pytest.mark.asyncio
    async def test_strips_bare_fences(self, processor):
        prompt_result = MagicMock()
        prompt_result.text = "```\nSELECT ?x WHERE { ?x a :Player }\n```"

        prompt_client = AsyncMock()
        prompt_client.prompt = AsyncMock(return_value=prompt_result)

        flow = MagicMock()
        flow.return_value = prompt_client

        ontology = _make_ontology_response(classes=SAMPLE_CLASSES)

        result = await processor._generate_sparql(
            flow, "question", ontology, [], 10
        )

        assert result == "SELECT ?x WHERE { ?x a :Player }"

    @pytest.mark.asyncio
    async def test_returns_empty_on_exception(self, processor):
        prompt_client = AsyncMock()
        prompt_client.prompt = AsyncMock(side_effect=RuntimeError("boom"))

        flow = MagicMock()
        flow.return_value = prompt_client

        ontology = _make_ontology_response(classes=SAMPLE_CLASSES)

        result = await processor._generate_sparql(
            flow, "question", ontology, [], 10
        )

        assert result == ""

    @pytest.mark.asyncio
    async def test_passes_resolved_entities_to_prompt(self, processor):
        from trustgraph.schema import ResolvedEntity

        prompt_result = MagicMock()
        prompt_result.text = "SELECT ?x WHERE { ?x a :Player }"

        prompt_client = AsyncMock()
        prompt_client.prompt = AsyncMock(return_value=prompt_result)

        flow = MagicMock()
        flow.return_value = prompt_client

        ontology = _make_ontology_response(
            classes=SAMPLE_CLASSES,
            obj_props=SAMPLE_OBJ_PROPS,
        )

        resolved = [
            ResolvedEntity(
                mention="Farage", uri="http://example.org/farage",
                rdf_type="Player", score=0.87,
            ),
        ]

        await processor._generate_sparql(
            flow, "question", ontology, resolved, 10
        )

        call_args = prompt_client.prompt.call_args
        variables = call_args[1]["variables"]
        assert len(variables["resolved_entities"]) == 1
        assert variables["resolved_entities"][0]["mention"] == "Farage"
        assert variables["resolved_entities"][0]["uri"] == "http://example.org/farage"
        assert variables["limit"] == 10


# ---------------------------------------------------------------------------
# _translate (full pipeline)
# ---------------------------------------------------------------------------

class TestTranslate:

    @pytest.mark.asyncio
    async def test_returns_error_when_no_ontology(self, processor):
        ontology_client = AsyncMock()
        ontology_client.request = AsyncMock(
            return_value=_make_ontology_response(
                error=Error(type="no-ontology", message="not loaded"),
            )
        )

        flow = MagicMock()
        flow.return_value = ontology_client

        request = QuestionToSparqlRequest(
            question="What?", collection="default", limit=10
        )

        result = await processor._translate(flow, request)

        assert result.error is not None
        assert result.error.type == "no-ontology"

    @pytest.mark.asyncio
    async def test_returns_sparql_and_entities(self, processor):
        ontology_response = _make_ontology_response(
            classes=SAMPLE_CLASSES,
            obj_props=SAMPLE_OBJ_PROPS,
            dt_props=SAMPLE_DT_PROPS,
        )

        entity_prompt_result = MagicMock()
        entity_prompt_result.object = {
            "entities": [{"mention": "Farage", "type": "Player"}]
        }

        sparql_prompt_result = MagicMock()
        sparql_prompt_result.text = "SELECT ?x WHERE { ?x a :Player }"

        ontology_client = AsyncMock()
        ontology_client.request = AsyncMock(return_value=ontology_response)

        prompt_client = AsyncMock()
        prompt_client.prompt = AsyncMock(
            side_effect=[entity_prompt_result, sparql_prompt_result]
        )

        embeddings_client = AsyncMock()
        embeddings_client.embed = AsyncMock(return_value=[[0.1, 0.2]])

        graph_client = AsyncMock()
        graph_client.query = AsyncMock(return_value=[
            FakeGraphMatch(
                entity=Term(type=IRI, iri="http://example.org/farage"),
                score=0.87,
            )
        ])

        def flow_dispatch(name):
            return {
                "ontology-request": ontology_client,
                "prompt-request": prompt_client,
                "embeddings-request": embeddings_client,
                "graph-embeddings-request": graph_client,
            }[name]

        flow = MagicMock(side_effect=flow_dispatch)

        request = QuestionToSparqlRequest(
            question="What choices does Farage have?",
            collection="default",
            limit=10,
        )

        result = await processor._translate(flow, request)

        assert result.error is None
        assert "SELECT" in result.sparql
        assert len(result.resolved_entities) == 1
        assert result.resolved_entities[0].uri == "http://example.org/farage"
