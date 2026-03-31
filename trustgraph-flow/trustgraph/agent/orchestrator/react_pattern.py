"""
ReactPattern — extracted from the existing agent_manager.py.

Implements the ReACT (Reasoning + Acting) loop: think, select a tool,
observe the result, repeat until a final answer is produced.
"""

import json
import logging
import uuid

from ... schema import AgentRequest, AgentResponse, AgentStep

from trustgraph.provenance import (
    agent_iteration_uri,
    agent_thought_uri,
    agent_observation_uri,
)

from ..react.agent_manager import AgentManager
from ..react.types import Action, Final
from ..tool_filter import get_next_state

from . pattern_base import PatternBase

logger = logging.getLogger(__name__)


class ReactPattern(PatternBase):
    """
    ReACT pattern: interleaved reasoning and action.

    Each iterate() call performs one reason/act cycle. If the LLM
    produces a Final answer the dialog completes; otherwise the action
    result is appended to history and a next-request is emitted.
    """

    async def iterate(self, request, respond, next, flow):

        streaming = getattr(request, 'streaming', False)
        session_id = getattr(request, 'session_id', '') or str(uuid.uuid4())
        collection = getattr(request, 'collection', 'default')

        history = self.build_history(request)
        iteration_num = len(history) + 1
        session_uri = self.processor.provenance_session_uri(session_id)

        # Emit session provenance on first iteration
        if iteration_num == 1:
            await self.emit_session_triples(
                flow, session_uri, request.question,
                request.user, collection, respond, streaming,
            )

        logger.info(f"ReactPattern iteration {iteration_num}: {request.question}")

        if len(history) >= self.processor.max_iterations:
            raise RuntimeError("Too many agent iterations")

        # Compute URIs upfront for message_id
        thought_msg_id = agent_thought_uri(session_id, iteration_num)
        observation_msg_id = agent_observation_uri(session_id, iteration_num)

        # Build callbacks
        think = self.make_think_callback(respond, streaming, message_id=thought_msg_id)
        observe = self.make_observe_callback(respond, streaming, message_id=observation_msg_id)
        answer_cb = self.make_answer_callback(respond, streaming)

        # Filter tools
        filtered_tools = self.filter_tools(
            self.processor.agent.tools, request,
        )

        # Create temporary agent with filtered tools and optional framing
        additional_context = self.processor.agent.additional_context
        framing = getattr(request, 'framing', '')
        if framing:
            if additional_context:
                additional_context = f"{additional_context}\n\n{framing}"
            else:
                additional_context = framing

        temp_agent = AgentManager(
            tools=filtered_tools,
            additional_context=additional_context,
        )

        context = self.make_context(
            flow, request.user,
            respond=respond, streaming=streaming,
        )

        # Set current explain URI so tools can link sub-traces
        context.current_explain_uri = agent_iteration_uri(
            session_id, iteration_num,
        )

        # Callback: emit Analysis+ToolUse triples before tool executes
        async def on_action(act):
            await self.emit_iteration_triples(
                flow, session_id, iteration_num, session_uri,
                act, request, respond, streaming,
            )

        act = await temp_agent.react(
            question=request.question,
            history=history,
            think=think,
            observe=observe,
            answer=answer_cb,
            context=context,
            streaming=streaming,
            on_action=on_action,
        )

        logger.debug(f"Action: {act}")

        if isinstance(act, Final):

            if isinstance(act.final, str):
                f = act.final
            else:
                f = json.dumps(act.final)

            # Emit final provenance
            await self.emit_final_triples(
                flow, session_id, iteration_num, session_uri,
                f, request, respond, streaming,
            )

            if self.is_subagent(request):
                await self.emit_subagent_completion(request, next, f)
            else:
                await self.send_final_response(
                    respond, streaming, f, already_streamed=streaming,
                )
            return

        # Emit observation provenance after tool execution
        await self.emit_observation_triples(
            flow, session_id, iteration_num,
            act.observation, request, respond,
        )

        history.append(act)

        # Handle state transitions
        next_state = request.state
        if act.name in filtered_tools:
            executed_tool = filtered_tools[act.name]
            next_state = get_next_state(executed_tool, request.state or "undefined")

        r = self.build_next_request(
            request, history, session_id, collection,
            streaming, next_state,
        )
        await next(r)

        logger.debug("ReactPattern iteration complete")
