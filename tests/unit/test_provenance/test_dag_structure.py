"""
DAG structure tests for provenance chains.

Verifies that the wasDerivedFrom chain has the expected shape for each
service. These tests catch structural regressions when new entities are
inserted into the chain (e.g. PatternDecision between session and first
iteration).

Expected chains:

  GraphRAG:     question → grounding → exploration → focus → synthesis
  DocumentRAG:  question → grounding → exploration → synthesis
  Agent React:  session → pattern-decision → iteration → (observation → iteration)* → final
  Agent Plan:   session → pattern-decision → plan → step-result(s) → synthesis
  Agent Super:  session → pattern-decision → decomposition → (fan-out) → finding(s) → synthesis
"""

import json
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from trustgraph.schema import (
    AgentRequest, AgentResponse, AgentStep, PlanStep,
    Triple, Term, IRI, LITERAL,
)
from trustgraph.base import PromptResult

from trustgraph.provenance.namespaces import (
    RDF_TYPE, PROV_WAS_DERIVED_FROM, GRAPH_RETRIEVAL,
    TG_AGENT_QUESTION, TG_GRAPH_RAG_QUESTION, TG_DOC_RAG_QUESTION,
    TG_GROUNDING, TG_EXPLORATION, TG_FOCUS, TG_SYNTHESIS,
    TG_ANALYSIS, TG_CONCLUSION, TG_PATTERN_DECISION,
    TG_PLAN_TYPE, TG_STEP_RESULT, TG_DECOMPOSITION,
    TG_OBSERVATION_TYPE,
    TG_PATTERN, TG_TASK_TYPE,
)

from trustgraph.retrieval.graph_rag.graph_rag import GraphRag
from trustgraph.retrieval.document_rag.document_rag import DocumentRag


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _collect_events(events):
    """Build a dict of explain_id → {types, derived_from, triples}."""
    result = {}
    for ev in events:
        eid = ev["explain_id"]
        triples = ev["triples"]
        types = {
            t.o.iri for t in triples
            if t.s.iri == eid and t.p.iri == RDF_TYPE
        }
        parents = [
            t.o.iri for t in triples
            if t.s.iri == eid and t.p.iri == PROV_WAS_DERIVED_FROM
        ]
        result[eid] = {
            "types": types,
            "derived_from": parents[0] if parents else None,
            "triples": triples,
        }
    return result


def _find_by_type(dag, rdf_type):
    """Find all event IDs that have the given rdf:type."""
    return [eid for eid, info in dag.items() if rdf_type in info["types"]]


def _assert_chain(dag, chain_types):
    """Assert that a linear wasDerivedFrom chain exists through the given types."""
    for i in range(1, len(chain_types)):
        parent_type = chain_types[i - 1]
        child_type = chain_types[i]
        parents = _find_by_type(dag, parent_type)
        children = _find_by_type(dag, child_type)
        assert parents, f"No entity with type {parent_type}"
        assert children, f"No entity with type {child_type}"
        # At least one child must derive from at least one parent
        linked = False
        for child_id in children:
            derived = dag[child_id]["derived_from"]
            if derived in parents:
                linked = True
                break
        assert linked, (
            f"No {child_type} derives from {parent_type}. "
            f"Children derive from: "
            f"{[dag[c]['derived_from'] for c in children]}"
        )


# ---------------------------------------------------------------------------
# GraphRAG DAG structure
# ---------------------------------------------------------------------------

class TestGraphRagDagStructure:
    """Verify: question → grounding → exploration → focus → synthesis"""

    @pytest.fixture
    def mock_clients(self):
        prompt_client = AsyncMock()
        embeddings_client = AsyncMock()
        graph_embeddings_client = AsyncMock()
        triples_client = AsyncMock()

        embeddings_client.embed.return_value = [[0.1, 0.2]]
        graph_embeddings_client.query.return_value = [
            MagicMock(entity=Term(type=IRI, iri="http://example.com/e1")),
        ]
        triples_client.query_stream.return_value = [
            Triple(
                s=Term(type=IRI, iri="http://example.com/e1"),
                p=Term(type=IRI, iri="http://example.com/p"),
                o=Term(type=LITERAL, value="value"),
            )
        ]
        triples_client.query.return_value = []

        async def mock_prompt(template_id, variables=None, **kwargs):
            if template_id == "extract-concepts":
                return PromptResult(response_type="text", text="concept")
            elif template_id == "kg-edge-scoring":
                edges = variables.get("knowledge", [])
                return PromptResult(
                    response_type="jsonl",
                    objects=[{"id": e["id"], "score": 10} for e in edges],
                )
            elif template_id == "kg-edge-reasoning":
                edges = variables.get("knowledge", [])
                return PromptResult(
                    response_type="jsonl",
                    objects=[{"id": e["id"], "reasoning": "relevant"} for e in edges],
                )
            elif template_id == "kg-synthesis":
                return PromptResult(response_type="text", text="Answer.")
            return PromptResult(response_type="text", text="")

        prompt_client.prompt.side_effect = mock_prompt
        return prompt_client, embeddings_client, graph_embeddings_client, triples_client

    @pytest.mark.asyncio
    async def test_dag_chain(self, mock_clients):
        rag = GraphRag(*mock_clients)
        events = []

        async def explain_cb(triples, explain_id):
            events.append({"explain_id": explain_id, "triples": triples})

        await rag.query(
            query="test", explain_callback=explain_cb, edge_score_limit=0,
        )

        dag = _collect_events(events)
        assert len(dag) == 5, f"Expected 5 events, got {len(dag)}"

        _assert_chain(dag, [
            TG_GRAPH_RAG_QUESTION,
            TG_GROUNDING,
            TG_EXPLORATION,
            TG_FOCUS,
            TG_SYNTHESIS,
        ])


# ---------------------------------------------------------------------------
# DocumentRAG DAG structure
# ---------------------------------------------------------------------------

class TestDocumentRagDagStructure:
    """Verify: question → grounding → exploration → synthesis"""

    @pytest.fixture
    def mock_clients(self):
        from trustgraph.schema import ChunkMatch

        prompt_client = AsyncMock()
        embeddings_client = AsyncMock()
        doc_embeddings_client = AsyncMock()
        fetch_chunk = AsyncMock(return_value="Chunk content.")

        embeddings_client.embed.return_value = [[0.1, 0.2]]
        doc_embeddings_client.query.return_value = [
            ChunkMatch(chunk_id="doc/c1", score=0.9),
        ]

        async def mock_prompt(template_id, variables=None, **kwargs):
            if template_id == "extract-concepts":
                return PromptResult(response_type="text", text="concept")
            return PromptResult(response_type="text", text="")

        prompt_client.prompt.side_effect = mock_prompt
        prompt_client.document_prompt.return_value = PromptResult(
            response_type="text", text="Answer.",
        )

        return prompt_client, embeddings_client, doc_embeddings_client, fetch_chunk

    @pytest.mark.asyncio
    async def test_dag_chain(self, mock_clients):
        rag = DocumentRag(*mock_clients)
        events = []

        async def explain_cb(triples, explain_id):
            events.append({"explain_id": explain_id, "triples": triples})

        await rag.query(
            query="test", explain_callback=explain_cb,
        )

        dag = _collect_events(events)
        assert len(dag) == 4, f"Expected 4 events, got {len(dag)}"

        _assert_chain(dag, [
            TG_DOC_RAG_QUESTION,
            TG_GROUNDING,
            TG_EXPLORATION,
            TG_SYNTHESIS,
        ])


# ---------------------------------------------------------------------------
# Agent DAG structure — tested via service.agent_request()
# ---------------------------------------------------------------------------

def _make_processor(tools=None):
    processor = MagicMock()
    processor.max_iterations = 10
    processor.save_answer_content = AsyncMock()

    def mock_session_uri(sid):
        return f"urn:trustgraph:agent:session:{sid}"
    processor.provenance_session_uri.side_effect = mock_session_uri

    agent = MagicMock()
    agent.tools = tools or {}
    agent.additional_context = ""
    processor.agents = {"default": agent}
    processor.aggregator = MagicMock()

    return processor


def _make_flow():
    producers = {}

    def factory(name):
        if name not in producers:
            producers[name] = AsyncMock()
        return producers[name]

    flow = MagicMock(side_effect=factory)
    flow.workspace = "default"
    return flow


def _collect_agent_events(respond_mock):
    events = []
    for call in respond_mock.call_args_list:
        resp = call[0][0]
        if isinstance(resp, AgentResponse) and resp.message_type == "explain":
            events.append({
                "explain_id": resp.explain_id,
                "triples": resp.explain_triples,
            })
    return events


class TestAgentReactDagStructure:
    """
    Via service.agent_request(), full two-iteration react chain:
      session → pattern-decision → iteration(1) → observation(1) → final

    Iteration 1: tool call → observation
    Iteration 2: final answer
    """

    def _make_service(self):
        from trustgraph.agent.orchestrator.service import Processor
        from trustgraph.agent.orchestrator.react_pattern import ReactPattern
        from trustgraph.agent.orchestrator.plan_pattern import PlanThenExecutePattern
        from trustgraph.agent.orchestrator.supervisor_pattern import SupervisorPattern

        mock_tool = MagicMock()
        mock_tool.name = "lookup"
        mock_tool.description = "Look things up"
        mock_tool.arguments = []
        mock_tool.groups = []
        mock_tool.states = {}
        mock_tool_impl = AsyncMock(return_value="42")
        mock_tool.implementation = MagicMock(return_value=mock_tool_impl)

        processor = _make_processor(tools={"lookup": mock_tool})

        service = Processor.__new__(Processor)
        service.max_iterations = 10
        service.save_answer_content = AsyncMock()
        service.provenance_session_uri = processor.provenance_session_uri
        service.agents = processor.agents
        service.aggregator = processor.aggregator

        service.react_pattern = ReactPattern(service)
        service.plan_pattern = PlanThenExecutePattern(service)
        service.supervisor_pattern = SupervisorPattern(service)
        service.meta_router = None

        return service

    @pytest.mark.asyncio
    async def test_dag_chain(self):
        from trustgraph.agent.react.types import Action, Final

        service = self._make_service()

        respond = AsyncMock()
        next_fn = AsyncMock()
        flow = _make_flow()
        session_id = str(uuid.uuid4())

        # Iteration 1: tool call → returns Action, triggers on_action + tool exec
        action = Action(
            thought="I need to look this up",
            name="lookup",
            arguments={"question": "6x7"},
            observation="",
        )

        with patch(
            "trustgraph.agent.orchestrator.react_pattern.AgentManager"
        ) as MockAM:
            mock_am = AsyncMock()
            MockAM.return_value = mock_am

            async def mock_react_iter1(on_action=None, **kwargs):
                if on_action:
                    await on_action(action)
                action.observation = "42"
                return action

            mock_am.react.side_effect = mock_react_iter1

            request1 = AgentRequest(
                question="What is 6x7?",
                collection="default",
                streaming=False,
                session_id=session_id,
                pattern="react",
                history=[],
            )

            await service.agent_request(request1, respond, next_fn, flow)

        # next_fn should have been called with updated history
        assert next_fn.called

        # Iteration 2: final answer
        final = Final(thought="The answer is 42", final="42")
        next_request = next_fn.call_args[0][0]

        with patch(
            "trustgraph.agent.orchestrator.react_pattern.AgentManager"
        ) as MockAM:
            mock_am = AsyncMock()
            MockAM.return_value = mock_am

            async def mock_react_iter2(**kwargs):
                return final

            mock_am.react.side_effect = mock_react_iter2

            await service.agent_request(next_request, respond, next_fn, flow)

        # Collect and verify DAG
        events = _collect_agent_events(respond)
        dag = _collect_events(events)

        session_ids = _find_by_type(dag, TG_AGENT_QUESTION)
        pd_ids = _find_by_type(dag, TG_PATTERN_DECISION)
        analysis_ids = _find_by_type(dag, TG_ANALYSIS)
        observation_ids = _find_by_type(dag, TG_OBSERVATION_TYPE)
        final_ids = _find_by_type(dag, TG_CONCLUSION)

        assert len(session_ids) == 1, f"Expected 1 session, got {len(session_ids)}"
        assert len(pd_ids) == 1, f"Expected 1 pattern-decision, got {len(pd_ids)}"
        assert len(analysis_ids) >= 1, f"Expected >=1 analysis, got {len(analysis_ids)}"
        assert len(observation_ids) >= 1, f"Expected >=1 observation, got {len(observation_ids)}"
        assert len(final_ids) == 1, f"Expected 1 final, got {len(final_ids)}"

        # Full chain:
        # session → pattern-decision
        assert dag[pd_ids[0]]["derived_from"] == session_ids[0]

        # pattern-decision → iteration(1)
        assert dag[analysis_ids[0]]["derived_from"] == pd_ids[0]

        # iteration(1) → observation(1)
        assert dag[observation_ids[0]]["derived_from"] == analysis_ids[0]

        # observation(1) → final
        assert dag[final_ids[0]]["derived_from"] == observation_ids[0]


class TestAgentPlanDagStructure:
    """
    Via service.agent_request():
      session → pattern-decision → plan → step-result → synthesis
    """

    @pytest.mark.asyncio
    async def test_dag_chain(self):
        from trustgraph.agent.orchestrator.service import Processor
        from trustgraph.agent.orchestrator.react_pattern import ReactPattern
        from trustgraph.agent.orchestrator.plan_pattern import PlanThenExecutePattern
        from trustgraph.agent.orchestrator.supervisor_pattern import SupervisorPattern

        # Mock tool
        mock_tool = MagicMock()
        mock_tool.name = "knowledge-query"
        mock_tool.description = "Query KB"
        mock_tool.arguments = []
        mock_tool.groups = []
        mock_tool.states = {}
        mock_tool_impl = AsyncMock(return_value="Found it")
        mock_tool.implementation = MagicMock(return_value=mock_tool_impl)

        processor = _make_processor(tools={"knowledge-query": mock_tool})

        service = Processor.__new__(Processor)
        service.max_iterations = 10
        service.save_answer_content = AsyncMock()
        service.provenance_session_uri = processor.provenance_session_uri
        service.agents = processor.agents
        service.aggregator = processor.aggregator

        service.react_pattern = ReactPattern(service)
        service.plan_pattern = PlanThenExecutePattern(service)
        service.supervisor_pattern = SupervisorPattern(service)
        service.meta_router = None

        respond = AsyncMock()
        next_fn = AsyncMock()
        flow = _make_flow()

        # Mock prompt client
        mock_prompt_client = AsyncMock()

        call_count = 0

        async def mock_prompt(id, variables=None, **kwargs):
            nonlocal call_count
            call_count += 1
            if id == "plan-create":
                return PromptResult(
                    response_type="jsonl",
                    objects=[{"goal": "Find info", "tool_hint": "knowledge-query", "depends_on": []}],
                )
            elif id == "plan-step-execute":
                return PromptResult(
                    response_type="json",
                    object={"tool": "knowledge-query", "arguments": {"question": "test"}},
                )
            elif id == "plan-synthesise":
                return PromptResult(response_type="text", text="Final answer.")
            return PromptResult(response_type="text", text="")

        mock_prompt_client.prompt.side_effect = mock_prompt

        def flow_factory(name):
            if name == "prompt-request":
                return mock_prompt_client
            return AsyncMock()
        flow.side_effect = flow_factory

        session_id = str(uuid.uuid4())

        # Iteration 1: planning
        request1 = AgentRequest(
            question="Test?",
            collection="default",
            streaming=False,
            session_id=session_id,
            pattern="plan-then-execute",
            history=[],
        )
        await service.agent_request(request1, respond, next_fn, flow)

        # Iteration 2: execute step (next_fn was called with updated request)
        assert next_fn.called
        next_request = next_fn.call_args[0][0]

        # Iteration 3: all steps done → synthesis
        # Simulate completed step in history
        next_request.history[-1].plan[0].status = "completed"
        next_request.history[-1].plan[0].result = "Found it"

        await service.agent_request(next_request, respond, next_fn, flow)

        events = _collect_agent_events(respond)
        dag = _collect_events(events)

        session_ids = _find_by_type(dag, TG_AGENT_QUESTION)
        pd_ids = _find_by_type(dag, TG_PATTERN_DECISION)
        plan_ids = _find_by_type(dag, TG_PLAN_TYPE)
        synthesis_ids = _find_by_type(dag, TG_SYNTHESIS)

        assert len(session_ids) == 1
        assert len(pd_ids) == 1
        assert len(plan_ids) == 1
        assert len(synthesis_ids) == 1

        # Chain: session → pattern-decision → plan → ... → synthesis
        assert dag[pd_ids[0]]["derived_from"] == session_ids[0]
        assert dag[plan_ids[0]]["derived_from"] == pd_ids[0]


class TestAgentSupervisorDagStructure:
    """
    Via service.agent_request():
      session → pattern-decision → decomposition → (fan-out)
    """

    @pytest.mark.asyncio
    async def test_dag_chain(self):
        from trustgraph.agent.orchestrator.service import Processor
        from trustgraph.agent.orchestrator.react_pattern import ReactPattern
        from trustgraph.agent.orchestrator.plan_pattern import PlanThenExecutePattern
        from trustgraph.agent.orchestrator.supervisor_pattern import SupervisorPattern

        processor = _make_processor()

        service = Processor.__new__(Processor)
        service.max_iterations = 10
        service.save_answer_content = AsyncMock()
        service.provenance_session_uri = processor.provenance_session_uri
        service.agents = processor.agents
        service.aggregator = processor.aggregator

        service.react_pattern = ReactPattern(service)
        service.plan_pattern = PlanThenExecutePattern(service)
        service.supervisor_pattern = SupervisorPattern(service)
        service.meta_router = None

        respond = AsyncMock()
        next_fn = AsyncMock()
        flow = _make_flow()

        mock_prompt_client = AsyncMock()
        mock_prompt_client.prompt.return_value = PromptResult(
            response_type="jsonl",
            objects=["Goal A", "Goal B"],
        )

        def flow_factory(name):
            if name == "prompt-request":
                return mock_prompt_client
            return AsyncMock()
        flow.side_effect = flow_factory

        request = AgentRequest(
            question="Research quantum computing",
            collection="default",
            streaming=False,
            session_id=str(uuid.uuid4()),
            pattern="supervisor",
            history=[],
        )

        await service.agent_request(request, respond, next_fn, flow)

        events = _collect_agent_events(respond)
        dag = _collect_events(events)

        session_ids = _find_by_type(dag, TG_AGENT_QUESTION)
        pd_ids = _find_by_type(dag, TG_PATTERN_DECISION)
        decomp_ids = _find_by_type(dag, TG_DECOMPOSITION)

        assert len(session_ids) == 1
        assert len(pd_ids) == 1
        assert len(decomp_ids) == 1

        # Chain: session → pattern-decision → decomposition
        assert dag[pd_ids[0]]["derived_from"] == session_ids[0]
        assert dag[decomp_ids[0]]["derived_from"] == pd_ids[0]

        # Fan-out should have been called
        assert next_fn.call_count == 2  # One per goal
