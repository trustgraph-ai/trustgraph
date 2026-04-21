"""
Integration tests for agent-orchestrator provenance chains.

Tests all three patterns by calling iterate() with mocked dependencies
and verifying the explain events emitted via respond().

Provenance chains:
  React:      session → iteration → (observation or final)
  Plan:       session → plan → step-result(s) → synthesis
  Supervisor: session → decomposition → finding(s) → synthesis
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass, field

from trustgraph.schema import (
    AgentRequest, AgentResponse, AgentStep, PlanStep,
)
from trustgraph.base import PromptResult

from trustgraph.provenance.namespaces import (
    RDF_TYPE, PROV_ENTITY, PROV_WAS_DERIVED_FROM,
    GRAPH_RETRIEVAL,
)

# Agent provenance type constants
from trustgraph.provenance.namespaces import (
    TG_AGENT_QUESTION,
    TG_ANALYSIS,
    TG_TOOL_USE,
    TG_OBSERVATION_TYPE,
    TG_CONCLUSION,
    TG_DECOMPOSITION,
    TG_FINDING,
    TG_PLAN_TYPE,
    TG_STEP_RESULT,
    TG_SYNTHESIS as TG_AGENT_SYNTHESIS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def find_triple(triples, predicate, subject=None):
    for t in triples:
        if t.p.iri == predicate:
            if subject is None or t.s.iri == subject:
                return t
    return None


def has_type(triples, subject, rdf_type):
    return any(
        t.s.iri == subject and t.p.iri == RDF_TYPE and t.o.iri == rdf_type
        for t in triples
    )


def derived_from(triples, subject):
    t = find_triple(triples, PROV_WAS_DERIVED_FROM, subject)
    return t.o.iri if t else None


def collect_explain_events(respond_mock):
    """Extract explain events from a respond mock's call history."""
    events = []
    for call in respond_mock.call_args_list:
        resp = call[0][0]
        if isinstance(resp, AgentResponse) and resp.message_type == "explain":
            events.append({
                "explain_id": resp.explain_id,
                "explain_graph": resp.explain_graph,
                "triples": resp.explain_triples,
            })
    return events


# ---------------------------------------------------------------------------
# Mock processor
# ---------------------------------------------------------------------------

def make_mock_processor(tools=None):
    """Build a mock processor with the minimal interface patterns need."""
    processor = MagicMock()
    processor.max_iterations = 10
    processor.save_answer_content = AsyncMock()

    # provenance_session_uri must return a real URI
    def mock_session_uri(session_id):
        return f"urn:trustgraph:agent:session:{session_id}"
    processor.provenance_session_uri.side_effect = mock_session_uri

    # Agent with tools
    agent = MagicMock()
    agent.tools = tools or {}
    agent.additional_context = ""
    processor.agent = agent

    # Aggregator for supervisor
    processor.aggregator = MagicMock()

    return processor


def make_mock_flow():
    """Build a mock flow that returns async mock producers."""
    producers = {}

    def flow_factory(name):
        if name not in producers:
            producers[name] = AsyncMock()
        return producers[name]

    flow = MagicMock(side_effect=flow_factory)
    flow._producers = producers
    return flow


def make_base_request(**kwargs):
    """Build a minimal AgentRequest."""
    defaults = dict(
        question="What is quantum computing?",
        state="",
        group=[],
        history=[],
        collection="default",
        streaming=False,
        session_id="test-session-123",
        conversation_id="",
        pattern="react",
        task_type="",
        framing="",
        correlation_id="",
        parent_session_id="",
        subagent_goal="",
        expected_siblings=0,
    )
    defaults.update(kwargs)
    return AgentRequest(**defaults)


# ---------------------------------------------------------------------------
# React pattern tests
# ---------------------------------------------------------------------------

class TestReactPatternProvenance:
    """
    React pattern chain: session → iteration → final
    (single iteration ending in Final answer)
    """

    @pytest.mark.asyncio
    async def test_single_iteration_final_answer(self):
        """
        A single react iteration that produces a Final answer should emit:
        session, iteration, final — in that order.
        """
        from trustgraph.agent.orchestrator.react_pattern import ReactPattern
        from trustgraph.agent.react.types import Action, Final

        processor = make_mock_processor()
        pattern = ReactPattern(processor)

        respond = AsyncMock()
        next_fn = AsyncMock()
        flow = make_mock_flow()

        request = make_base_request()

        # Mock AgentManager.react to call on_action then return Final
        with patch(
            'trustgraph.agent.orchestrator.react_pattern.AgentManager'
        ) as MockAM:
            mock_am = AsyncMock()
            MockAM.return_value = mock_am

            final = Final(
                thought="I know the answer",
                final="Quantum computing uses qubits.",
            )

            async def mock_react(question, history, think, observe, answer,
                                 context, streaming, on_action, **kwargs):
                # Simulate the on_action callback before returning Final
                if on_action:
                    await on_action(Action(
                        thought="I know the answer",
                        name="final",
                        arguments={},
                        observation="",
                    ))
                return final

            mock_am.react.side_effect = mock_react

            await pattern.iterate(request, respond, next_fn, flow)

        events = collect_explain_events(respond)

        # Should have 3 events: session, iteration, final
        assert len(events) == 3, (
            f"Expected 3 explain events (session, iteration, final), "
            f"got {len(events)}: {[e['explain_id'] for e in events]}"
        )

        # Check types
        assert has_type(events[0]["triples"], events[0]["explain_id"], TG_AGENT_QUESTION)
        assert has_type(events[1]["triples"], events[1]["explain_id"], TG_ANALYSIS)
        assert has_type(events[2]["triples"], events[2]["explain_id"], TG_CONCLUSION)

        # Check derivation chain
        all_triples = []
        for e in events:
            all_triples.extend(e["triples"])

        uris = [e["explain_id"] for e in events]

        # iteration derives from session
        assert derived_from(all_triples, uris[1]) == uris[0]
        # final derives from session (first iteration, no prior observation)
        assert derived_from(all_triples, uris[2]) == uris[0]

    @pytest.mark.asyncio
    async def test_iteration_with_tool_call(self):
        """
        A react iteration that calls a tool (not Final) should emit:
        session, iteration, observation — then call next() for continuation.
        """
        from trustgraph.agent.orchestrator.react_pattern import ReactPattern
        from trustgraph.agent.react.types import Action

        # Create a mock tool
        mock_tool = MagicMock()
        mock_tool.name = "knowledge-query"
        mock_tool.description = "Query the knowledge base"
        mock_tool.arguments = []
        mock_tool.groups = []
        mock_tool.states = {}
        mock_tool_impl = AsyncMock(return_value="The answer is 42")
        mock_tool.implementation = MagicMock(return_value=mock_tool_impl)

        processor = make_mock_processor(
            tools={"knowledge-query": mock_tool}
        )
        pattern = ReactPattern(processor)

        respond = AsyncMock()
        next_fn = AsyncMock()
        flow = make_mock_flow()

        request = make_base_request()

        action = Action(
            thought="I need to look this up",
            name="knowledge-query",
            arguments={"question": "What is quantum computing?"},
            observation="Quantum computing uses qubits.",
        )

        with patch(
            'trustgraph.agent.orchestrator.react_pattern.AgentManager'
        ) as MockAM:
            mock_am = AsyncMock()
            MockAM.return_value = mock_am

            async def mock_react(question, history, think, observe, answer,
                                 context, streaming, on_action, **kwargs):
                if on_action:
                    await on_action(action)
                return action

            mock_am.react.side_effect = mock_react

            await pattern.iterate(request, respond, next_fn, flow)

        events = collect_explain_events(respond)

        # Should have 3 events: session, iteration, observation
        assert len(events) == 3, (
            f"Expected 3 explain events (session, iteration, observation), "
            f"got {len(events)}: {[e['explain_id'] for e in events]}"
        )

        assert has_type(events[0]["triples"], events[0]["explain_id"], TG_AGENT_QUESTION)
        assert has_type(events[1]["triples"], events[1]["explain_id"], TG_ANALYSIS)
        assert has_type(events[2]["triples"], events[2]["explain_id"], TG_OBSERVATION_TYPE)

        # next() should have been called to continue the loop
        assert next_fn.called

    @pytest.mark.asyncio
    async def test_all_triples_in_retrieval_graph(self):
        """All explain triples should be in urn:graph:retrieval."""
        from trustgraph.agent.orchestrator.react_pattern import ReactPattern
        from trustgraph.agent.react.types import Action, Final

        processor = make_mock_processor()
        pattern = ReactPattern(processor)
        respond = AsyncMock()
        flow = make_mock_flow()

        with patch(
            'trustgraph.agent.orchestrator.react_pattern.AgentManager'
        ) as MockAM:
            mock_am = AsyncMock()
            MockAM.return_value = mock_am

            async def mock_react(question, history, think, observe, answer,
                                 context, streaming, on_action, **kwargs):
                if on_action:
                    await on_action(Action(
                        thought="done", name="final",
                        arguments={}, observation="",
                    ))
                return Final(thought="done", final="answer")

            mock_am.react.side_effect = mock_react
            await pattern.iterate(
                make_base_request(), respond, AsyncMock(), flow,
            )

        for event in collect_explain_events(respond):
            for t in event["triples"]:
                assert t.g == GRAPH_RETRIEVAL


# ---------------------------------------------------------------------------
# Plan-then-execute pattern tests
# ---------------------------------------------------------------------------

class TestPlanPatternProvenance:
    """
    Plan pattern chain:
      Planning iteration: session → plan
      Execution iterations: step-result(s) → synthesis
    """

    @pytest.mark.asyncio
    async def test_planning_iteration_emits_session_and_plan(self):
        """
        The first iteration (planning) should emit:
        session, plan — then call next() with the plan in history.
        """
        from trustgraph.agent.orchestrator.plan_pattern import PlanThenExecutePattern

        processor = make_mock_processor()
        pattern = PlanThenExecutePattern(processor)

        respond = AsyncMock()
        next_fn = AsyncMock()
        flow = make_mock_flow()

        # Mock prompt client for plan creation
        mock_prompt_client = AsyncMock()
        mock_prompt_client.prompt.return_value = PromptResult(
            response_type="jsonl",
            objects=[
                {"goal": "Find information", "tool_hint": "knowledge-query", "depends_on": []},
                {"goal": "Summarise findings", "tool_hint": "", "depends_on": [0]},
            ],
        )

        def flow_factory(name):
            if name == "prompt-request":
                return mock_prompt_client
            return AsyncMock()
        flow.side_effect = flow_factory

        request = make_base_request(pattern="plan")

        await pattern.iterate(request, respond, next_fn, flow)

        events = collect_explain_events(respond)

        # Should have 2 events: session, plan
        assert len(events) == 2, (
            f"Expected 2 explain events (session, plan), "
            f"got {len(events)}: {[e['explain_id'] for e in events]}"
        )

        assert has_type(events[0]["triples"], events[0]["explain_id"], TG_AGENT_QUESTION)
        assert has_type(events[1]["triples"], events[1]["explain_id"], TG_PLAN_TYPE)

        # Plan should derive from session
        all_triples = []
        for e in events:
            all_triples.extend(e["triples"])
        assert derived_from(all_triples, events[1]["explain_id"]) == events[0]["explain_id"]

        # next() should have been called with plan in history
        assert next_fn.called

    @pytest.mark.asyncio
    async def test_execution_iteration_emits_step_result(self):
        """
        An execution iteration should emit a step-result event.
        """
        from trustgraph.agent.orchestrator.plan_pattern import PlanThenExecutePattern

        # Create a mock tool
        mock_tool = MagicMock()
        mock_tool.name = "knowledge-query"
        mock_tool.description = "Query KB"
        mock_tool.arguments = []
        mock_tool.groups = []
        mock_tool.states = {}
        mock_tool_impl = AsyncMock(return_value="Found the answer")
        mock_tool.implementation = MagicMock(return_value=mock_tool_impl)

        processor = make_mock_processor(
            tools={"knowledge-query": mock_tool}
        )
        pattern = PlanThenExecutePattern(processor)

        respond = AsyncMock()
        next_fn = AsyncMock()
        flow = make_mock_flow()

        # Mock prompt for step execution
        mock_prompt_client = AsyncMock()
        mock_prompt_client.prompt.return_value = PromptResult(
            response_type="json",
            object={
                "tool": "knowledge-query",
                "arguments": {"question": "quantum computing"},
            },
        )

        def flow_factory(name):
            if name == "prompt-request":
                return mock_prompt_client
            return AsyncMock()
        flow.side_effect = flow_factory

        # Request with plan already in history (second iteration)
        plan_step = AgentStep(
            thought="Created plan",
            action="plan",
            arguments={},
            observation="[]",
            step_type="plan",
            plan=[
                PlanStep(goal="Find info", tool_hint="knowledge-query",
                         depends_on=[], status="pending", result=""),
            ],
        )
        request = make_base_request(
            pattern="plan",
            history=[plan_step],
        )

        await pattern.iterate(request, respond, next_fn, flow)

        events = collect_explain_events(respond)

        # Should have step-result (no session on iteration > 1)
        step_events = [
            e for e in events
            if has_type(e["triples"], e["explain_id"], TG_STEP_RESULT)
        ]
        assert len(step_events) == 1, (
            f"Expected 1 step-result event, got {len(step_events)}"
        )

    @pytest.mark.asyncio
    async def test_synthesis_after_all_steps_complete(self):
        """
        When all plan steps are completed, synthesis should be emitted.
        """
        from trustgraph.agent.orchestrator.plan_pattern import PlanThenExecutePattern

        processor = make_mock_processor()
        pattern = PlanThenExecutePattern(processor)

        respond = AsyncMock()
        next_fn = AsyncMock()
        flow = make_mock_flow()

        # Mock prompt for synthesis
        mock_prompt_client = AsyncMock()
        mock_prompt_client.prompt.return_value = PromptResult(response_type="text", text="The synthesised answer.")

        def flow_factory(name):
            if name == "prompt-request":
                return mock_prompt_client
            return AsyncMock()
        flow.side_effect = flow_factory

        # Request with all steps completed
        exec_step = AgentStep(
            thought="Executing step",
            action="knowledge-query",
            arguments={},
            observation="Result",
            step_type="execute",
            plan=[
                PlanStep(goal="Find info", tool_hint="knowledge-query",
                         depends_on=[], status="completed", result="Found it"),
            ],
        )
        request = make_base_request(
            pattern="plan",
            history=[exec_step],
        )

        await pattern.iterate(request, respond, next_fn, flow)

        events = collect_explain_events(respond)

        # Should have synthesis event
        synth_events = [
            e for e in events
            if has_type(e["triples"], e["explain_id"], TG_AGENT_SYNTHESIS)
        ]
        assert len(synth_events) == 1, (
            f"Expected 1 synthesis event, got {len(synth_events)}"
        )


# ---------------------------------------------------------------------------
# Supervisor pattern tests
# ---------------------------------------------------------------------------

class TestSupervisorPatternProvenance:
    """
    Supervisor pattern chain:
      Decompose: session → decomposition
      (Fan-out to subagents happens externally)
      Synthesise: synthesis (derives from findings)
    """

    @pytest.mark.asyncio
    async def test_decompose_emits_session_and_decomposition(self):
        """
        The decompose phase should emit: session, decomposition.
        """
        from trustgraph.agent.orchestrator.supervisor_pattern import SupervisorPattern

        processor = make_mock_processor()
        pattern = SupervisorPattern(processor)

        respond = AsyncMock()
        next_fn = AsyncMock()
        flow = make_mock_flow()

        # Mock prompt for decomposition
        mock_prompt_client = AsyncMock()
        mock_prompt_client.prompt.return_value = PromptResult(
            response_type="jsonl",
            objects=[
                "What is quantum computing?",
                "What are qubits?",
            ],
        )

        def flow_factory(name):
            if name == "prompt-request":
                return mock_prompt_client
            return AsyncMock()
        flow.side_effect = flow_factory

        request = make_base_request(pattern="supervisor")

        await pattern.iterate(request, respond, next_fn, flow)

        events = collect_explain_events(respond)

        # Should have 2 events: session, decomposition
        assert len(events) == 2, (
            f"Expected 2 explain events (session, decomposition), "
            f"got {len(events)}: {[e['explain_id'] for e in events]}"
        )

        assert has_type(events[0]["triples"], events[0]["explain_id"], TG_AGENT_QUESTION)
        assert has_type(events[1]["triples"], events[1]["explain_id"], TG_DECOMPOSITION)

        # Decomposition derives from session
        all_triples = []
        for e in events:
            all_triples.extend(e["triples"])
        assert derived_from(all_triples, events[1]["explain_id"]) == events[0]["explain_id"]

    @pytest.mark.asyncio
    async def test_synthesis_emits_after_subagent_results(self):
        """
        When subagent results arrive, synthesis should be emitted.
        """
        from trustgraph.agent.orchestrator.supervisor_pattern import SupervisorPattern

        processor = make_mock_processor()
        pattern = SupervisorPattern(processor)

        respond = AsyncMock()
        next_fn = AsyncMock()
        flow = make_mock_flow()

        # Mock prompt for synthesis
        mock_prompt_client = AsyncMock()
        mock_prompt_client.prompt.return_value = PromptResult(response_type="text", text="The combined answer.")

        def flow_factory(name):
            if name == "prompt-request":
                return mock_prompt_client
            return AsyncMock()
        flow.side_effect = flow_factory

        # Request with subagent results in history
        synth_step = AgentStep(
            thought="",
            action="synthesise",
            arguments={},
            observation="",
            step_type="synthesise",
            subagent_results={
                "What is quantum computing?": "It uses qubits",
                "What are qubits?": "Quantum bits",
            },
        )
        request = make_base_request(
            pattern="supervisor",
            history=[synth_step],
        )

        await pattern.iterate(request, respond, next_fn, flow)

        events = collect_explain_events(respond)

        # Should have synthesis event (no session on iteration > 1)
        synth_events = [
            e for e in events
            if has_type(e["triples"], e["explain_id"], TG_AGENT_SYNTHESIS)
        ]
        assert len(synth_events) == 1

    @pytest.mark.asyncio
    async def test_decompose_fans_out_subagents(self):
        """The decompose phase should call next() for each subagent goal."""
        from trustgraph.agent.orchestrator.supervisor_pattern import SupervisorPattern

        processor = make_mock_processor()
        pattern = SupervisorPattern(processor)

        respond = AsyncMock()
        next_fn = AsyncMock()
        flow = make_mock_flow()

        mock_prompt_client = AsyncMock()
        mock_prompt_client.prompt.return_value = PromptResult(
            response_type="jsonl",
            objects=["Goal A", "Goal B", "Goal C"],
        )

        def flow_factory(name):
            if name == "prompt-request":
                return mock_prompt_client
            return AsyncMock()
        flow.side_effect = flow_factory

        request = make_base_request(pattern="supervisor")

        await pattern.iterate(request, respond, next_fn, flow)

        # 3 subagent requests fanned out
        assert next_fn.call_count == 3
