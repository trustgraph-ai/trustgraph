"""
Base class for agent patterns.

Provides shared infrastructure used by all patterns: tool filtering,
provenance emission, streaming callbacks, history management, and
librarian integration.
"""

import json
import logging
import uuid
from datetime import datetime

from ... schema import AgentRequest, AgentResponse, AgentStep, Error
from ... schema import Triples, Metadata

from trustgraph.provenance import (
    agent_session_uri,
    agent_iteration_uri,
    agent_thought_uri,
    agent_observation_uri,
    agent_final_uri,
    agent_session_triples,
    agent_iteration_triples,
    agent_final_triples,
    set_graph,
    GRAPH_RETRIEVAL,
)

from ..react.types import Action, Final
from ..tool_filter import filter_tools_by_group_and_state, get_next_state

logger = logging.getLogger(__name__)


class UserAwareContext:
    """Wraps flow interface to inject user context for tools that need it."""

    def __init__(self, flow, user):
        self._flow = flow
        self._user = user

    def __call__(self, service_name):
        client = self._flow(service_name)
        if service_name in (
            "structured-query-request",
            "row-embeddings-query-request",
        ):
            client._current_user = self._user
        return client


class PatternBase:
    """
    Shared infrastructure for all agent patterns.

    Subclasses implement iterate() to perform one iteration of their
    pattern-specific logic.
    """

    def __init__(self, processor):
        self.processor = processor

    def is_subagent(self, request):
        """Check if this request is running as a subagent of a supervisor."""
        return bool(getattr(request, 'correlation_id', ''))

    async def emit_subagent_completion(self, request, next, answer_text):
        """Signal completion back to the orchestrator via the agent request
        queue. Instead of sending the final answer to the client, send a
        completion message so the aggregator can collect it."""

        completion_step = AgentStep(
            thought="Subagent completed",
            action="complete",
            arguments={},
            observation=answer_text,
            step_type="subagent-completion",
        )

        completion_request = AgentRequest(
            question=request.question,
            state="",
            group=getattr(request, 'group', []),
            history=[completion_step],
            user=request.user,
            collection=getattr(request, 'collection', 'default'),
            streaming=False,
            session_id=getattr(request, 'session_id', ''),
            conversation_id=getattr(request, 'conversation_id', ''),
            pattern="",
            correlation_id=request.correlation_id,
            parent_session_id=getattr(request, 'parent_session_id', ''),
            subagent_goal=getattr(request, 'subagent_goal', ''),
            expected_siblings=getattr(request, 'expected_siblings', 0),
        )

        await next(completion_request)
        logger.info(
            f"Subagent completion emitted for "
            f"correlation={request.correlation_id}, "
            f"goal={getattr(request, 'subagent_goal', '')}"
        )

    def filter_tools(self, tools, request):
        """Apply group/state filtering to the tool set."""
        return filter_tools_by_group_and_state(
            tools=tools,
            requested_groups=getattr(request, 'group', None),
            current_state=getattr(request, 'state', None),
        )

    def make_context(self, flow, user):
        """Create a user-aware context wrapper."""
        return UserAwareContext(flow, user)

    def build_history(self, request):
        """Convert AgentStep history into Action objects."""
        if not request.history:
            return []
        return [
            Action(
                thought=h.thought,
                name=h.action,
                arguments=h.arguments,
                observation=h.observation,
            )
            for h in request.history
        ]

    # ---- Streaming callbacks ------------------------------------------------

    def make_think_callback(self, respond, streaming):
        """Create the think callback for streaming/non-streaming."""
        async def think(x, is_final=False):
            logger.debug(f"Think: {x} (is_final={is_final})")
            if streaming:
                r = AgentResponse(
                    chunk_type="thought",
                    content=x,
                    end_of_message=is_final,
                    end_of_dialog=False,
                )
            else:
                r = AgentResponse(
                    chunk_type="thought",
                    content=x,
                    end_of_message=True,
                    end_of_dialog=False,
                )
            await respond(r)
        return think

    def make_observe_callback(self, respond, streaming):
        """Create the observe callback for streaming/non-streaming."""
        async def observe(x, is_final=False):
            logger.debug(f"Observe: {x} (is_final={is_final})")
            if streaming:
                r = AgentResponse(
                    chunk_type="observation",
                    content=x,
                    end_of_message=is_final,
                    end_of_dialog=False,
                )
            else:
                r = AgentResponse(
                    chunk_type="observation",
                    content=x,
                    end_of_message=True,
                    end_of_dialog=False,
                )
            await respond(r)
        return observe

    def make_answer_callback(self, respond, streaming):
        """Create the answer callback for streaming/non-streaming."""
        async def answer(x):
            logger.debug(f"Answer: {x}")
            if streaming:
                r = AgentResponse(
                    chunk_type="answer",
                    content=x,
                    end_of_message=False,
                    end_of_dialog=False,
                )
            else:
                r = AgentResponse(
                    chunk_type="answer",
                    content=x,
                    end_of_message=True,
                    end_of_dialog=False,
                )
            await respond(r)
        return answer

    # ---- Provenance emission ------------------------------------------------

    async def emit_session_triples(self, flow, session_uri, question, user,
                                   collection, respond, streaming):
        """Emit provenance triples for a new session."""
        timestamp = datetime.utcnow().isoformat() + "Z"
        triples = set_graph(
            agent_session_triples(session_uri, question, timestamp),
            GRAPH_RETRIEVAL,
        )
        await flow("explainability").send(Triples(
            metadata=Metadata(
                id=session_uri,
                user=user,
                collection=collection,
            ),
            triples=triples,
        ))
        logger.debug(f"Emitted session triples for {session_uri}")

        if streaming:
            await respond(AgentResponse(
                chunk_type="explain",
                content="",
                explain_id=session_uri,
                explain_graph=GRAPH_RETRIEVAL,
            ))

    async def emit_iteration_triples(self, flow, session_id, iteration_num,
                                     session_uri, act, request, respond,
                                     streaming):
        """Emit provenance triples for an iteration and save to librarian."""
        iteration_uri = agent_iteration_uri(session_id, iteration_num)

        if iteration_num > 1:
            iter_question_uri = None
            iter_previous_uri = agent_iteration_uri(session_id, iteration_num - 1)
        else:
            iter_question_uri = session_uri
            iter_previous_uri = None

        # Save thought to librarian
        thought_doc_id = None
        if act.thought:
            thought_doc_id = (
                f"urn:trustgraph:agent:{session_id}/i{iteration_num}/thought"
            )
            try:
                await self.processor.save_answer_content(
                    doc_id=thought_doc_id,
                    user=request.user,
                    content=act.thought,
                    title=f"Agent Thought: {act.name}",
                )
            except Exception as e:
                logger.warning(f"Failed to save thought to librarian: {e}")
                thought_doc_id = None

        # Save observation to librarian
        observation_doc_id = None
        if act.observation:
            observation_doc_id = (
                f"urn:trustgraph:agent:{session_id}/i{iteration_num}/observation"
            )
            try:
                await self.processor.save_answer_content(
                    doc_id=observation_doc_id,
                    user=request.user,
                    content=act.observation,
                    title=f"Agent Observation: {act.name}",
                )
            except Exception as e:
                logger.warning(f"Failed to save observation to librarian: {e}")
                observation_doc_id = None

        thought_entity_uri = agent_thought_uri(session_id, iteration_num)
        observation_entity_uri = agent_observation_uri(session_id, iteration_num)

        iter_triples = set_graph(
            agent_iteration_triples(
                iteration_uri,
                question_uri=iter_question_uri,
                previous_uri=iter_previous_uri,
                action=act.name,
                arguments=act.arguments,
                thought_uri=thought_entity_uri if thought_doc_id else None,
                thought_document_id=thought_doc_id,
                observation_uri=observation_entity_uri if observation_doc_id else None,
                observation_document_id=observation_doc_id,
            ),
            GRAPH_RETRIEVAL,
        )
        await flow("explainability").send(Triples(
            metadata=Metadata(
                id=iteration_uri,
                user=request.user,
                collection=getattr(request, 'collection', 'default'),
            ),
            triples=iter_triples,
        ))
        logger.debug(f"Emitted iteration triples for {iteration_uri}")

        if streaming:
            await respond(AgentResponse(
                chunk_type="explain",
                content="",
                explain_id=iteration_uri,
                explain_graph=GRAPH_RETRIEVAL,
            ))

    async def emit_final_triples(self, flow, session_id, iteration_num,
                                 session_uri, answer_text, request, respond,
                                 streaming):
        """Emit provenance triples for the final answer and save to librarian."""
        final_uri = agent_final_uri(session_id)

        if iteration_num > 1:
            final_question_uri = None
            final_previous_uri = agent_iteration_uri(session_id, iteration_num - 1)
        else:
            final_question_uri = session_uri
            final_previous_uri = None

        # Save answer to librarian
        answer_doc_id = None
        if answer_text:
            answer_doc_id = f"urn:trustgraph:agent:{session_id}/answer"
            try:
                await self.processor.save_answer_content(
                    doc_id=answer_doc_id,
                    user=request.user,
                    content=answer_text,
                    title=f"Agent Answer: {request.question[:50]}...",
                )
                logger.debug(f"Saved answer to librarian: {answer_doc_id}")
            except Exception as e:
                logger.warning(f"Failed to save answer to librarian: {e}")
                answer_doc_id = None

        final_triples = set_graph(
            agent_final_triples(
                final_uri,
                question_uri=final_question_uri,
                previous_uri=final_previous_uri,
                document_id=answer_doc_id,
            ),
            GRAPH_RETRIEVAL,
        )
        await flow("explainability").send(Triples(
            metadata=Metadata(
                id=final_uri,
                user=request.user,
                collection=getattr(request, 'collection', 'default'),
            ),
            triples=final_triples,
        ))
        logger.debug(f"Emitted final triples for {final_uri}")

        if streaming:
            await respond(AgentResponse(
                chunk_type="explain",
                content="",
                explain_id=final_uri,
                explain_graph=GRAPH_RETRIEVAL,
            ))

    # ---- Response helpers ---------------------------------------------------

    async def prompt_as_answer(self, client, prompt_id, variables,
                               respond, streaming):
        """Call a prompt template, forwarding chunks as answer
        AgentResponse messages when streaming is enabled.

        Returns the full accumulated answer text (needed for provenance).
        """
        if streaming:
            accumulated = []

            async def on_chunk(text, end_of_stream):
                if text:
                    accumulated.append(text)
                    await respond(AgentResponse(
                        chunk_type="answer",
                        content=text,
                        end_of_message=False,
                        end_of_dialog=False,
                    ))

            await client.prompt(
                id=prompt_id,
                variables=variables,
                streaming=True,
                chunk_callback=on_chunk,
            )

            return "".join(accumulated)
        else:
            return await client.prompt(
                id=prompt_id,
                variables=variables,
            )

    async def send_final_response(self, respond, streaming, answer_text,
                                  already_streamed=False):
        """Send the answer content and end-of-dialog marker.

        Args:
            already_streamed: If True, answer chunks were already sent
                via streaming callbacks (e.g. ReactPattern). Only the
                end-of-dialog marker is emitted.
        """
        if streaming and not already_streamed:
            # Answer wasn't streamed yet — send it as a chunk first
            if answer_text:
                await respond(AgentResponse(
                    chunk_type="answer",
                    content=answer_text,
                    end_of_message=False,
                    end_of_dialog=False,
                ))
        if streaming:
            # End-of-dialog marker
            await respond(AgentResponse(
                chunk_type="answer",
                content="",
                end_of_message=True,
                end_of_dialog=True,
            ))
        else:
            await respond(AgentResponse(
                chunk_type="answer",
                content=answer_text,
                end_of_message=True,
                end_of_dialog=True,
            ))

    def build_next_request(self, request, history, session_id, collection,
                           streaming, next_state):
        """Build the AgentRequest for the next iteration."""
        return AgentRequest(
            question=request.question,
            state=next_state,
            group=getattr(request, 'group', []),
            history=[
                AgentStep(
                    thought=h.thought,
                    action=h.name,
                    arguments={k: str(v) for k, v in h.arguments.items()},
                    observation=h.observation,
                )
                for h in history
            ],
            user=request.user,
            collection=collection,
            streaming=streaming,
            session_id=session_id,
            # Preserve orchestration fields
            conversation_id=getattr(request, 'conversation_id', ''),
            pattern=getattr(request, 'pattern', ''),
            task_type=getattr(request, 'task_type', ''),
            framing=getattr(request, 'framing', ''),
            correlation_id=getattr(request, 'correlation_id', ''),
            parent_session_id=getattr(request, 'parent_session_id', ''),
            subagent_goal=getattr(request, 'subagent_goal', ''),
            expected_siblings=getattr(request, 'expected_siblings', 0),
        )

    async def iterate(self, request, respond, next, flow):
        """
        Perform one iteration of this pattern.

        Must be implemented by subclasses.
        """
        raise NotImplementedError
