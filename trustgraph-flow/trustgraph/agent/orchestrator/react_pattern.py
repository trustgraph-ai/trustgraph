"""
ReactPattern — extracted from the existing agent_manager.py.

Implements the ReACT (Reasoning + Acting) loop: think, select a tool,
observe the result, repeat until a final answer is produced.
"""

import json
import logging
import uuid

from ... schema import AgentRequest, AgentResponse, AgentStep

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

        # Build callbacks
        think = self.make_think_callback(respond, streaming)
        observe = self.make_observe_callback(respond, streaming)
        answer_cb = self.make_answer_callback(respond, streaming)

        # Filter tools
        filtered_tools = self.filter_tools(
            self.processor.agent.tools, request,
        )
        logger.info(
            f"Filtered from {len(self.processor.agent.tools)} "
            f"to {len(filtered_tools)} available tools"
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

        context = self.make_context(flow, request.user)

        act = await temp_agent.react(
            question=request.question,
            history=history,
            think=think,
            observe=observe,
            answer=answer_cb,
            context=context,
            streaming=streaming,
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

            await self.send_final_response(
                respond, streaming, f, already_streamed=streaming,
            )
            return

        # Not final — emit iteration provenance and send next request
        await self.emit_iteration_triples(
            flow, session_id, iteration_num, session_uri,
            act, request, respond, streaming,
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
