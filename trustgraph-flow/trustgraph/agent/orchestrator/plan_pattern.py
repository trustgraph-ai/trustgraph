"""
PlanThenExecutePattern — structured planning followed by step execution.

Phase 1 (planning): LLM produces a structured plan of steps.
Phase 2 (execution): Each step is executed via single-shot tool call.
"""

import json
import logging
import uuid

from ... schema import AgentRequest, AgentResponse, AgentStep, PlanStep

from trustgraph.provenance import (
    agent_step_result_uri as make_step_result_uri,
    agent_thought_uri,
    agent_observation_uri,
    agent_synthesis_uri,
)

from . pattern_base import PatternBase, UsageTracker

logger = logging.getLogger(__name__)


class PlanThenExecutePattern(PatternBase):
    """
    Plan-then-Execute pattern.

    History tracks the current phase via AgentStep.step_type:
      - "plan" step: contains the plan in step.plan
      - "execute" step: a normal react iteration executing a plan step

    On the first call (empty history), a planning iteration is run.
    Subsequent calls execute the next pending plan step via ReACT.
    """

    async def iterate(self, request, respond, next, flow, usage=None):

        if usage is None:
            usage = UsageTracker()

        streaming = getattr(request, 'streaming', False)
        session_id = getattr(request, 'session_id', '') or str(uuid.uuid4())
        collection = getattr(request, 'collection', 'default')

        history = self.build_history(request)
        iteration_num = len(request.history) + 1
        session_uri = self.processor.provenance_session_uri(session_id)

        # Emit session provenance on first iteration
        if iteration_num == 1:
            await self.emit_session_triples(
                flow, session_uri, request.question,
                request.user, collection, respond, streaming,
            )

        logger.info(
            f"PlanThenExecutePattern iteration {iteration_num}: "
            f"{request.question}"
        )

        if iteration_num >= self.processor.max_iterations:
            raise RuntimeError("Too many agent iterations")

        # Determine current phase by checking history for a plan step
        plan = self._extract_plan(request.history)

        if plan is None:
            await self._planning_iteration(
                request, respond, next, flow,
                session_id, collection, streaming, session_uri,
                iteration_num, usage=usage,
            )
        else:
            await self._execution_iteration(
                request, respond, next, flow,
                session_id, collection, streaming, session_uri,
                iteration_num, plan, usage=usage,
            )

    def _extract_plan(self, history):
        """Find the most recent plan from history.

        Checks execute steps first (they carry the updated plan with
        completion statuses), then falls back to the original plan step.
        """
        if not history:
            return None
        for step in reversed(history):
            if step.plan:
                return list(step.plan)
        return None

    def _find_next_pending_step(self, plan):
        """Return index of the next pending step, or None if all done."""
        for i, step in enumerate(plan):
            if getattr(step, 'status', 'pending') == 'pending':
                return i
        return None

    async def _planning_iteration(self, request, respond, next, flow,
                                  session_id, collection, streaming,
                                  session_uri, iteration_num, usage=None):
        """Ask the LLM to produce a structured plan."""

        think = self.make_think_callback(respond, streaming)

        tools = self.filter_tools(self.processor.agent.tools, request)
        framing = getattr(request, 'framing', '')

        context = self.make_context(
            flow, request.user,
            respond=respond, streaming=streaming,
        )
        client = context("prompt-request")

        # Use the plan-create prompt template
        result = await client.prompt(
            id="plan-create",
            variables={
                "question": request.question,
                "framing": framing,
                "tools": [
                    {"name": t.name, "description": t.description}
                    for t in tools.values()
                ],
            },
        )
        if usage:
            usage.track(result)

        plan_steps = result.objects
        # Validate we got a list
        if not isinstance(plan_steps, list) or not plan_steps:
            logger.warning("plan-create returned invalid result, falling back to single step")
            plan_steps = [{"goal": "Answer the question directly", "tool_hint": "", "depends_on": []}]

        # Emit thought about the plan
        thought_text = f"Created plan with {len(plan_steps)} steps"
        await think(thought_text, is_final=True)

        # Emit plan provenance
        step_goals = [ps.get("goal", "") for ps in plan_steps]
        await self.emit_plan_triples(
            flow, session_id, session_uri, step_goals,
            request.user, collection, respond, streaming,
        )

        # Build PlanStep objects
        plan_agent_steps = [
            PlanStep(
                goal=ps.get("goal", ""),
                tool_hint=ps.get("tool_hint", ""),
                depends_on=ps.get("depends_on", []),
                status="pending",
                result="",
            )
            for ps in plan_steps
        ]

        # Create a plan step in history
        plan_history_step = AgentStep(
            thought=thought_text,
            action="plan",
            arguments={},
            observation=json.dumps(plan_steps),
            step_type="plan",
            plan=plan_agent_steps,
        )

        # Build next request with plan in history
        new_history = list(request.history) + [plan_history_step]
        r = AgentRequest(
            question=request.question,
            state=request.state,
            group=getattr(request, 'group', []),
            history=new_history,
            user=request.user,
            collection=collection,
            streaming=streaming,
            session_id=session_id,
            conversation_id=getattr(request, 'conversation_id', ''),
            pattern=getattr(request, 'pattern', ''),
            task_type=getattr(request, 'task_type', ''),
            framing=getattr(request, 'framing', ''),
            correlation_id=getattr(request, 'correlation_id', ''),
            parent_session_id=getattr(request, 'parent_session_id', ''),
            subagent_goal=getattr(request, 'subagent_goal', ''),
            expected_siblings=getattr(request, 'expected_siblings', 0),
        )
        await next(r)

    async def _execution_iteration(self, request, respond, next, flow,
                                   session_id, collection, streaming,
                                   session_uri, iteration_num, plan,
                                   usage=None):
        """Execute the next pending plan step via single-shot tool call."""

        pending_idx = self._find_next_pending_step(plan)

        if pending_idx is None:
            # All steps done — synthesise final answer
            await self._synthesise(
                request, respond, next, flow,
                session_id, collection, streaming,
                session_uri, iteration_num, plan,
                usage=usage,
            )
            return

        current_step = plan[pending_idx]
        goal = getattr(current_step, 'goal', '') or str(current_step)

        logger.info(f"Executing plan step {pending_idx}: {goal}")

        thought_msg_id = agent_thought_uri(session_id, iteration_num)
        observation_msg_id = agent_observation_uri(session_id, iteration_num)

        think = self.make_think_callback(respond, streaming, message_id=thought_msg_id)
        observe = self.make_observe_callback(respond, streaming, message_id=observation_msg_id)

        # Gather results from dependencies
        previous_results = []
        depends_on = getattr(current_step, 'depends_on', [])
        if depends_on:
            for dep_idx in depends_on:
                if 0 <= dep_idx < len(plan):
                    dep_step = plan[dep_idx]
                    dep_result = getattr(dep_step, 'result', '')
                    if dep_result:
                        previous_results.append({
                            "index": dep_idx,
                            "result": dep_result,
                        })

        tools = self.filter_tools(self.processor.agent.tools, request)
        context = self.make_context(
            flow, request.user,
            respond=respond, streaming=streaming,
        )

        # Set current explain URI so tools can link sub-traces
        context.current_explain_uri = make_step_result_uri(
            session_id, pending_idx,
        )

        client = context("prompt-request")

        # Single-shot: ask LLM which tool + arguments to use for this goal
        result = await client.prompt(
            id="plan-step-execute",
            variables={
                "goal": goal,
                "previous_results": previous_results,
                "tools": [
                    {
                        "name": t.name,
                        "description": t.description,
                        "arguments": [
                            {"name": a.name, "type": a.type, "description": a.description}
                            for a in t.arguments
                        ],
                    }
                    for t in tools.values()
                ],
            },
        )
        if usage:
            usage.track(result)

        tool_call = result.object
        tool_name = tool_call.get("tool", "")
        tool_arguments = tool_call.get("arguments", {})

        await think(
            f"Step {pending_idx}: {goal} → calling {tool_name}",
            is_final=True,
        )

        # Invoke the tool directly
        if tool_name in tools:
            tool = tools[tool_name]
            resp = await tool.implementation(context).invoke(**tool_arguments)
            step_result = resp.strip() if isinstance(resp, str) else str(resp).strip()
        else:
            logger.warning(
                f"Plan step {pending_idx}: LLM selected unknown tool "
                f"'{tool_name}', available: {list(tools.keys())}"
            )
            step_result = f"Error: tool '{tool_name}' not found"

        await observe(step_result, is_final=True)

        # Update plan step status
        plan[pending_idx] = PlanStep(
            goal=goal,
            tool_hint=getattr(current_step, 'tool_hint', ''),
            depends_on=getattr(current_step, 'depends_on', []),
            status="completed",
            result=step_result,
        )

        # Emit step result provenance
        await self.emit_step_result_triples(
            flow, session_id, pending_idx, goal, step_result,
            request.user, collection, respond, streaming,
        )

        # Build execution step for history
        exec_step = AgentStep(
            thought=f"Executing plan step {pending_idx}: {goal}",
            action=tool_name,
            arguments={k: str(v) for k, v in tool_arguments.items()},
            observation=step_result,
            step_type="execute",
            plan=plan,
        )

        new_history = list(request.history) + [exec_step]

        r = AgentRequest(
            question=request.question,
            state=request.state,
            group=getattr(request, 'group', []),
            history=new_history,
            user=request.user,
            collection=collection,
            streaming=streaming,
            session_id=session_id,
            conversation_id=getattr(request, 'conversation_id', ''),
            pattern=getattr(request, 'pattern', ''),
            task_type=getattr(request, 'task_type', ''),
            framing=getattr(request, 'framing', ''),
            correlation_id=getattr(request, 'correlation_id', ''),
            parent_session_id=getattr(request, 'parent_session_id', ''),
            subagent_goal=getattr(request, 'subagent_goal', ''),
            expected_siblings=getattr(request, 'expected_siblings', 0),
        )
        await next(r)

    async def _synthesise(self, request, respond, next, flow,
                          session_id, collection, streaming,
                          session_uri, iteration_num, plan,
                          usage=None):
        """Synthesise a final answer from all completed plan step results."""

        think = self.make_think_callback(respond, streaming)
        framing = getattr(request, 'framing', '')

        context = self.make_context(
            flow, request.user,
            respond=respond, streaming=streaming,
        )
        client = context("prompt-request")

        # Use the plan-synthesise prompt template
        steps_data = []
        for i, step in enumerate(plan):
            steps_data.append({
                "index": i,
                "goal": getattr(step, 'goal', f'Step {i}'),
                "result": getattr(step, 'result', ''),
            })

        await think("Synthesising final answer from plan results", is_final=True)

        synthesis_msg_id = agent_synthesis_uri(session_id)

        response_text = await self.prompt_as_answer(
            client, "plan-synthesise",
            variables={
                "question": request.question,
                "framing": framing,
                "steps": steps_data,
            },
            respond=respond,
            streaming=streaming,
            message_id=synthesis_msg_id,
            usage=usage,
        )

        # Emit synthesis provenance (links back to last step result)
        last_step_uri = make_step_result_uri(session_id, len(plan) - 1)
        await self.emit_synthesis_triples(
            flow, session_id, last_step_uri,
            response_text, request.user, collection, respond, streaming,
        )

        if self.is_subagent(request):
            await self.emit_subagent_completion(request, next, response_text)
        else:
            await self.send_final_response(
                respond, streaming, response_text, already_streamed=streaming,
                message_id=synthesis_msg_id,
                usage=usage,
            )
