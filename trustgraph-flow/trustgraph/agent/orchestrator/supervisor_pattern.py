"""
SupervisorPattern — decomposes a query into subagent goals, fans out,
then synthesises results when all subagents complete.

Phase 1 (decompose): LLM breaks the query into independent sub-goals.
Fan-out: Each sub-goal is emitted as a new AgentRequest on the agent
         request topic, carrying a correlation_id and parent_session_id.
Phase 2 (synthesise): Triggered when the aggregator detects all
         subagents have completed. The supervisor fetches results and
         produces the final answer.
"""

import json
import logging
import uuid

from ... schema import AgentRequest, AgentResponse, AgentStep

from ..react.types import Action, Final

from . pattern_base import PatternBase

logger = logging.getLogger(__name__)

MAX_SUBAGENTS = 5


class SupervisorPattern(PatternBase):
    """
    Supervisor pattern: decompose, fan-out, synthesise.

    History tracks phase via AgentStep.step_type:
      - "decompose": the decomposition step (subagent goals in arguments)
      - "synthesise": triggered by aggregator with results in subagent_results
    """

    async def iterate(self, request, respond, next, flow):

        streaming = getattr(request, 'streaming', False)
        session_id = getattr(request, 'session_id', '') or str(uuid.uuid4())
        collection = getattr(request, 'collection', 'default')
        iteration_num = len(request.history) + 1
        session_uri = self.processor.provenance_session_uri(session_id)

        # Emit session provenance on first iteration
        if iteration_num == 1:
            await self.emit_session_triples(
                flow, session_uri, request.question,
                request.user, collection, respond, streaming,
            )

        logger.info(
            f"SupervisorPattern iteration {iteration_num}: {request.question}"
        )

        # Check if this is a synthesis request (has subagent_results)
        has_results = bool(
            request.history
            and any(
                getattr(h, 'step_type', '') == 'decompose'
                for h in request.history
            )
            and any(
                getattr(h, 'subagent_results', None)
                for h in request.history
            )
        )

        if has_results:
            await self._synthesise(
                request, respond, next, flow,
                session_id, collection, streaming,
                session_uri, iteration_num,
            )
        else:
            await self._decompose_and_fanout(
                request, respond, next, flow,
                session_id, collection, streaming,
                session_uri, iteration_num,
            )

    async def _decompose_and_fanout(self, request, respond, next, flow,
                                    session_id, collection, streaming,
                                    session_uri, iteration_num):
        """Decompose the question into sub-goals and fan out subagents."""

        think = self.make_think_callback(respond, streaming)
        framing = getattr(request, 'framing', '')

        tools = self.filter_tools(self.processor.agent.tools, request)

        context = self.make_context(flow, request.user)
        client = context("prompt-request")

        # Use the supervisor-decompose prompt template
        goals = await client.prompt(
            id="supervisor-decompose",
            variables={
                "question": request.question,
                "framing": framing,
                "max_subagents": MAX_SUBAGENTS,
                "tools": [
                    {"name": t.name, "description": t.description}
                    for t in tools.values()
                ],
            },
        )

        # Validate result
        if not isinstance(goals, list):
            goals = []
        goals = [g for g in goals if isinstance(g, str)]
        goals = goals[:MAX_SUBAGENTS]

        if not goals:
            goals = [request.question]

        await think(
            f"Decomposed into {len(goals)} sub-goals: {goals}",
            is_final=True,
        )

        # Generate correlation ID for this fan-out
        correlation_id = str(uuid.uuid4())

        # Emit decomposition provenance
        decompose_act = Action(
            thought=f"Decomposed into {len(goals)} sub-goals",
            name="decompose",
            arguments={"goals": json.dumps(goals), "correlation_id": correlation_id},
            observation=f"Fanning out {len(goals)} subagents",
        )
        await self.emit_iteration_triples(
            flow, session_id, iteration_num, session_uri,
            decompose_act, request, respond, streaming,
        )

        # Fan out: emit a subagent request for each goal
        for i, goal in enumerate(goals):
            subagent_session = str(uuid.uuid4())
            sub_request = AgentRequest(
                question=goal,
                state="",
                group=getattr(request, 'group', []),
                history=[],
                user=request.user,
                collection=collection,
                streaming=False,  # Subagents don't stream
                session_id=subagent_session,
                conversation_id=getattr(request, 'conversation_id', ''),
                pattern="react",  # Subagents use react by default
                task_type=getattr(request, 'task_type', ''),
                framing=getattr(request, 'framing', ''),
                correlation_id=correlation_id,
                parent_session_id=session_id,
                subagent_goal=goal,
                expected_siblings=len(goals),
            )
            await next(sub_request)
            logger.info(f"Fan-out: emitted subagent {i} for goal: {goal}")

        # NOTE: The supervisor stops here. The aggregator will detect
        # when all subagents complete and emit a synthesis request
        # with the results populated.
        logger.info(
            f"Supervisor fan-out complete: {len(goals)} subagents, "
            f"correlation_id={correlation_id}"
        )

    async def _synthesise(self, request, respond, next, flow,
                          session_id, collection, streaming,
                          session_uri, iteration_num):
        """Synthesise final answer from subagent results."""

        think = self.make_think_callback(respond, streaming)
        framing = getattr(request, 'framing', '')

        # Collect subagent results from history
        subagent_results = {}
        for step in request.history:
            results = getattr(step, 'subagent_results', None)
            if results:
                subagent_results.update(results)

        if not subagent_results:
            logger.warning("Synthesis called with no subagent results")
            subagent_results = {"(no results)": "No subagent results available"}

        context = self.make_context(flow, request.user)
        client = context("prompt-request")

        await think("Synthesising final answer from sub-agent results", is_final=True)

        response_text = await self.prompt_as_answer(
            client, "supervisor-synthesise",
            variables={
                "question": request.question,
                "framing": framing,
                "results": [
                    {"goal": goal, "result": result}
                    for goal, result in subagent_results.items()
                ],
            },
            respond=respond,
            streaming=streaming,
        )

        await self.emit_final_triples(
            flow, session_id, iteration_num, session_uri,
            response_text, request, respond, streaming,
        )
        await self.send_final_response(
            respond, streaming, response_text, already_streamed=streaming,
        )
