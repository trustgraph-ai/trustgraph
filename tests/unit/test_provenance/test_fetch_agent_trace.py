"""
Tests for ExplainabilityClient.fetch_agent_trace walking the provenance
chain written by the agent orchestrator, including the PatternDecision
entity that sits between the session and the first step.
"""

from trustgraph.schema import IRI
from trustgraph.provenance import (
    agent_session_uri,
    agent_pattern_decision_uri,
    agent_iteration_uri,
    agent_observation_uri,
    agent_final_uri,
    agent_plan_uri,
    agent_step_result_uri,
    agent_synthesis_uri,
    agent_session_triples,
    agent_pattern_decision_triples,
    agent_iteration_triples,
    agent_observation_triples,
    agent_final_triples,
    agent_plan_triples,
    agent_step_result_triples,
    agent_synthesis_triples,
)
from trustgraph.api.explainability import (
    ExplainabilityClient,
    ExplainEntity,
    PatternDecision,
    Analysis,
    Observation,
    Conclusion,
    Plan,
    StepResult,
    Synthesis,
)


SESSION_ID = "s1"
SESSION = agent_session_uri(SESSION_ID)
PATTERN_DECISION = agent_pattern_decision_uri(SESSION_ID)


def _wire_term(term):
    if term.type == IRI:
        return {"t": "i", "i": term.iri}
    return {"t": "l", "v": term.value}


class FakeFlow:
    """In-memory stand-in for the triples_query API used by the client."""

    def __init__(self, triples):
        self.triples = list(triples)

    def triples_query(self, s=None, p=None, o=None, g=None,
                      collection=None, limit=100):
        result = []
        for t in self.triples:
            ts = _wire_term(t.s)
            tp = _wire_term(t.p)
            to = _wire_term(t.o)
            if s is not None and ts.get("i") != s:
                continue
            if p is not None and tp.get("i") != p:
                continue
            if o is not None and (to.get("i") or to.get("v")) != o:
                continue
            result.append({"s": ts, "p": tp, "o": to})
        return result[:limit]


def _parse(triples):
    """Parse builder output for the pattern decision entity."""
    tuples = [
        (t.s.iri, t.p.iri, t.o.iri if t.o.type == IRI else t.o.value)
        for t in triples
    ]
    return ExplainEntity.from_triples(PATTERN_DECISION, tuples)


def _fetch(triples):
    client = ExplainabilityClient(FakeFlow(triples), retry_delay=0.0)
    return client.fetch_agent_trace(SESSION)


def _session():
    return agent_session_triples(
        SESSION, "What is the capital of France?", "2026-11-01T09:00:00Z",
    )


def _react_steps(first_parent):
    """Two ReAct iterations and a final answer, as the orchestrator links them."""
    i1 = agent_iteration_uri(SESSION_ID, 1)
    o1 = agent_observation_uri(SESSION_ID, 1)
    i2 = agent_iteration_uri(SESSION_ID, 2)
    o2 = agent_observation_uri(SESSION_ID, 2)
    return (
        agent_iteration_triples(
            i1, question_uri=first_parent, action="knowledge-query",
            step_number=1,
        )
        + agent_observation_triples(o1, i1, tool_duration_ms=120)
        + agent_iteration_triples(
            i2, previous_uri=o1, action="calculator", step_number=2,
        )
        + agent_observation_triples(o2, i2)
        + agent_final_triples(
            agent_final_uri(SESSION_ID), previous_uri=o2,
            termination_reason="final-answer",
        )
    )


class TestPatternDecisionParsing:

    def test_pattern_and_task_type(self):
        entity = _parse(agent_pattern_decision_triples(
            PATTERN_DECISION, SESSION, "react", "research",
        ))

        assert isinstance(entity, PatternDecision)
        assert entity.entity_type == "pattern-decision"
        assert entity.pattern == "react"
        assert entity.task_type == "research"

    def test_task_type_is_optional(self):
        entity = _parse(agent_pattern_decision_triples(
            PATTERN_DECISION, SESSION, "plan-then-execute",
        ))

        assert isinstance(entity, PatternDecision)
        assert entity.pattern == "plan-then-execute"
        assert entity.task_type == ""


class TestFetchAgentTrace:

    def test_react_chain_through_pattern_decision(self):
        trace = _fetch(
            _session()
            + agent_pattern_decision_triples(
                PATTERN_DECISION, SESSION, "react", "general",
            )
            + _react_steps(PATTERN_DECISION)
        )

        assert trace["question"].query == "What is the capital of France?"

        steps = trace["steps"]
        assert [type(s) for s in steps] == [
            PatternDecision, Analysis, Observation,
            Analysis, Observation, Conclusion,
        ]
        assert steps[0].pattern == "react"
        assert steps[1].action == "knowledge-query"
        assert steps[2].tool_duration_ms == 120
        assert steps[3].action == "calculator"
        assert steps[5].termination_reason == "final-answer"

    def test_plan_chain_through_pattern_decision(self):
        plan = agent_plan_uri(SESSION_ID)
        step = agent_step_result_uri(SESSION_ID, 0)
        trace = _fetch(
            _session()
            + agent_pattern_decision_triples(
                PATTERN_DECISION, SESSION, "plan-then-execute",
            )
            + agent_plan_triples(plan, PATTERN_DECISION, ["Find the capital"])
            + agent_step_result_triples(step, plan, "Find the capital")
            + agent_synthesis_triples(
                agent_synthesis_uri(SESSION_ID), step,
                termination_reason="plan-complete",
            )
        )

        steps = trace["steps"]
        assert [type(s) for s in steps] == [
            PatternDecision, Plan, StepResult, Synthesis,
        ]
        assert steps[0].pattern == "plan-then-execute"
        assert steps[1].steps == ["Find the capital"]
        assert steps[3].termination_reason == "plan-complete"

    def test_chain_without_pattern_decision(self):
        trace = _fetch(_session() + _react_steps(SESSION))

        assert [type(s) for s in trace["steps"]] == [
            Analysis, Observation, Analysis, Observation, Conclusion,
        ]
