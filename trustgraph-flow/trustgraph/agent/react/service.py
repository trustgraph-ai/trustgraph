"""
Simple agent infrastructure broadly implements the ReAct flow.
"""

import asyncio
import base64
import json
import re
import sys
import functools
import logging
import uuid
from datetime import datetime

# Module logger
logger = logging.getLogger(__name__)

from ... base import AgentService, TextCompletionClientSpec, PromptClientSpec
from ... base import GraphRagClientSpec, ToolClientSpec, StructuredQueryClientSpec
from ... base import RowEmbeddingsQueryClientSpec, EmbeddingsClientSpec
from ... base import ProducerSpec
from ... base import Consumer, Producer
from ... base import ConsumerMetrics, ProducerMetrics

from ... schema import AgentRequest, AgentResponse, AgentStep, Error
from ... schema import Triples, Metadata
from ... schema import LibrarianRequest, LibrarianResponse, DocumentMetadata
from ... schema import librarian_request_queue, librarian_response_queue

# Provenance imports for agent explainability
from trustgraph.provenance import (
    agent_session_uri,
    agent_iteration_uri,
    agent_thought_uri,
    agent_observation_uri,
    agent_final_uri,
    agent_session_triples,
    agent_iteration_triples,
    agent_observation_triples,
    agent_final_triples,
    set_graph,
    GRAPH_RETRIEVAL,
)

from . tools import KnowledgeQueryImpl, TextCompletionImpl, McpToolImpl, PromptImpl, StructuredQueryImpl, RowEmbeddingsQueryImpl, ToolServiceImpl
from . agent_manager import AgentManager
from ..tool_filter import validate_tool_config, filter_tools_by_group_and_state, get_next_state

from . types import Final, Action, Tool, Argument

default_ident = "agent-manager"
default_max_iterations = 10
default_librarian_request_queue = librarian_request_queue
default_librarian_response_queue = librarian_response_queue

class Processor(AgentService):

    def __init__(self, **params):

        id = params.get("id")

        self.max_iterations = int(
            params.get("max_iterations", default_max_iterations)
        )

        self.config_key = params.get("config_type", "agent")

        super(Processor, self).__init__(
            **params | {
                "id": id,
                "max_iterations": self.max_iterations,
                "config_type": self.config_key,
            }
        )

        self.agent = AgentManager(
            tools={},
            additional_context="",
        )

        # Track active tool service clients for cleanup
        self.tool_service_clients = {}

        self.register_config_handler(
            self.on_tools_config, types=["tool", "tool-service"]
        )

        self.register_specification(
            TextCompletionClientSpec(
                request_name = "text-completion-request",
                response_name = "text-completion-response",
            )
        )

        self.register_specification(
            GraphRagClientSpec(
                request_name = "graph-rag-request",
                response_name = "graph-rag-response",
            )
        )

        self.register_specification(
            PromptClientSpec(
                request_name = "prompt-request",
                response_name = "prompt-response",
            )
        )

        self.register_specification(
            ToolClientSpec(
                request_name = "mcp-tool-request",
                response_name = "mcp-tool-response",
            )
        )

        self.register_specification(
            StructuredQueryClientSpec(
                request_name = "structured-query-request",
                response_name = "structured-query-response",
            )
        )

        self.register_specification(
            EmbeddingsClientSpec(
                request_name = "embeddings-request",
                response_name = "embeddings-response",
            )
        )

        self.register_specification(
            RowEmbeddingsQueryClientSpec(
                request_name = "row-embeddings-query-request",
                response_name = "row-embeddings-query-response",
            )
        )

        # Explainability producer for agent provenance triples
        self.register_specification(
            ProducerSpec(
                name = "explainability",
                schema = Triples,
            )
        )

        # Librarian client for storing answer content
        librarian_request_q = params.get(
            "librarian_request_queue", default_librarian_request_queue
        )
        librarian_response_q = params.get(
            "librarian_response_queue", default_librarian_response_queue
        )

        librarian_request_metrics = ProducerMetrics(
            processor=id, flow=None, name="librarian-request"
        )

        self.librarian_request_producer = Producer(
            backend=self.pubsub,
            topic=librarian_request_q,
            schema=LibrarianRequest,
            metrics=librarian_request_metrics,
        )

        librarian_response_metrics = ConsumerMetrics(
            processor=id, flow=None, name="librarian-response"
        )

        self.librarian_response_consumer = Consumer(
            taskgroup=self.taskgroup,
            backend=self.pubsub,
            flow=None,
            topic=librarian_response_q,
            subscriber=f"{id}-librarian",
            schema=LibrarianResponse,
            handler=self.on_librarian_response,
            metrics=librarian_response_metrics,
        )

        # Pending librarian requests: request_id -> asyncio.Future
        self.pending_librarian_requests = {}

    async def start(self):
        await super(Processor, self).start()
        await self.librarian_request_producer.start()
        await self.librarian_response_consumer.start()

    async def on_librarian_response(self, msg, consumer, flow):
        """Handle responses from the librarian service."""
        response = msg.value()
        request_id = msg.properties().get("id")

        if request_id in self.pending_librarian_requests:
            future = self.pending_librarian_requests.pop(request_id)
            future.set_result(response)

    async def save_answer_content(self, doc_id, user, content, title=None, timeout=120):
        """
        Save answer content to the librarian.

        Args:
            doc_id: ID for the answer document
            user: User ID
            content: Answer text content
            title: Optional title
            timeout: Request timeout in seconds

        Returns:
            The document ID on success
        """
        request_id = str(uuid.uuid4())

        doc_metadata = DocumentMetadata(
            id=doc_id,
            user=user,
            kind="text/plain",
            title=title or "Agent Answer",
            document_type="answer",
        )

        request = LibrarianRequest(
            operation="add-document",
            document_id=doc_id,
            document_metadata=doc_metadata,
            content=base64.b64encode(content.encode("utf-8")).decode("utf-8"),
            user=user,
        )

        # Create future for response
        future = asyncio.get_event_loop().create_future()
        self.pending_librarian_requests[request_id] = future

        try:
            # Send request
            await self.librarian_request_producer.send(
                request, properties={"id": request_id}
            )

            # Wait for response
            response = await asyncio.wait_for(future, timeout=timeout)

            if response.error:
                raise RuntimeError(
                    f"Librarian error saving answer: {response.error.type}: {response.error.message}"
                )

            return doc_id

        except asyncio.TimeoutError:
            self.pending_librarian_requests.pop(request_id, None)
            raise RuntimeError(f"Timeout saving answer document {doc_id}")

    async def on_tools_config(self, config, version):

        logger.info(f"Loading configuration version {version}")

        try:

            tools = {}

            # Load tool-service configurations first
            tool_services = {}
            if "tool-service" in config:
                for service_id, service_value in config["tool-service"].items():
                    service_data = json.loads(service_value)
                    tool_services[service_id] = service_data
                    logger.debug(f"Loaded tool-service config: {service_id}")

            logger.info(f"Loaded {len(tool_services)} tool-service configurations")

            # Load tool configurations from the new location
            if "tool" in config:
                for tool_id, tool_value in config["tool"].items():
                    data = json.loads(tool_value)
                    
                    impl_id = data.get("type")
                    name = data.get("name")
                    
                    # Create the appropriate implementation
                    if impl_id == "knowledge-query":
                        impl = functools.partial(
                            KnowledgeQueryImpl, 
                            collection=data.get("collection")
                        )
                        arguments = KnowledgeQueryImpl.get_arguments()
                    elif impl_id == "text-completion":
                        impl = TextCompletionImpl
                        arguments = TextCompletionImpl.get_arguments()
                    elif impl_id == "mcp-tool":
                        # For MCP tools, arguments come from config (similar to prompt tools)
                        config_args = data.get("arguments", [])
                        arguments = [
                            Argument(
                                name=arg.get("name"),
                                type=arg.get("type"),
                                description=arg.get("description")
                            )
                            for arg in config_args
                        ]
                        impl = functools.partial(
                            McpToolImpl, 
                            mcp_tool_id=data.get("mcp-tool"),
                            arguments=arguments
                        )
                    elif impl_id == "prompt":
                        # For prompt tools, arguments come from config
                        config_args = data.get("arguments", [])
                        arguments = [
                            Argument(
                                name=arg.get("name"),
                                type=arg.get("type"),
                                description=arg.get("description")
                            )
                            for arg in config_args
                        ]
                        impl = functools.partial(
                            PromptImpl,
                            template_id=data.get("template"),
                            arguments=arguments
                        )
                    elif impl_id == "structured-query":
                        impl = functools.partial(
                            StructuredQueryImpl,
                            collection=data.get("collection"),
                            user=None  # User will be provided dynamically via context
                        )
                        arguments = StructuredQueryImpl.get_arguments()
                    elif impl_id == "row-embeddings-query":
                        impl = functools.partial(
                            RowEmbeddingsQueryImpl,
                            schema_name=data.get("schema-name"),
                            collection=data.get("collection"),
                            user=None,  # User will be provided dynamically via context
                            index_name=data.get("index-name"),  # Optional filter
                            limit=int(data.get("limit", 10))  # Max results
                        )
                        arguments = RowEmbeddingsQueryImpl.get_arguments()
                    elif impl_id == "tool-service":
                        # Dynamic tool service - look up the service config
                        service_ref = data.get("service")
                        if not service_ref:
                            raise RuntimeError(
                                f"Tool {name} has type 'tool-service' but no 'service' reference"
                            )
                        if service_ref not in tool_services:
                            raise RuntimeError(
                                f"Tool {name} references unknown tool-service '{service_ref}'"
                            )

                        service_config = tool_services[service_ref]
                        request_queue = service_config.get("request-queue")
                        response_queue = service_config.get("response-queue")
                        if not request_queue or not response_queue:
                            raise RuntimeError(
                                f"Tool-service '{service_ref}' must define 'request-queue' and 'response-queue'"
                            )

                        # Build config values from tool config
                        # Extract any config params defined by the service
                        config_params = service_config.get("config-params", [])
                        config_values = {}
                        for param in config_params:
                            param_name = param.get("name") if isinstance(param, dict) else param
                            if param_name in data:
                                config_values[param_name] = data[param_name]
                            elif isinstance(param, dict) and param.get("required", False):
                                raise RuntimeError(
                                    f"Tool {name} missing required config param '{param_name}'"
                                )

                        # Arguments come from tool config
                        config_args = data.get("arguments", [])
                        arguments = [
                            Argument(
                                name=arg.get("name"),
                                type=arg.get("type"),
                                description=arg.get("description")
                            )
                            for arg in config_args
                        ]

                        # Store queues for the implementation
                        impl = functools.partial(
                            ToolServiceImpl,
                            request_queue=request_queue,
                            response_queue=response_queue,
                            config_values=config_values,
                            arguments=arguments,
                            processor=self,
                        )
                    else:
                        raise RuntimeError(
                            f"Tool type {impl_id} not known"
                        )
                    
                    # Validate tool configuration
                    validate_tool_config(data)
                    
                    tools[name] = Tool(
                        name=name,
                        description=data.get("description"),
                        implementation=impl,
                        config=data,  # Store full config for reference
                        arguments=arguments,
                    )
            
            # Load additional context from agent config if it exists
            additional = None
            if self.config_key in config:
                agent_config = config[self.config_key]
                additional = agent_config.get("additional-context", None)
            
            self.agent = AgentManager(
                tools=tools,
                additional_context=additional
            )

            logger.info(f"Loaded {len(tools)} tools")
            logger.info("Tool configuration reloaded.")

        except Exception as e:

            logger.error(f"on_tools_config Exception: {e}", exc_info=True)
            logger.error("Configuration reload failed")

    async def agent_request(self, request, respond, next, flow):

        try:

            # Check if streaming is enabled
            streaming = getattr(request, 'streaming', False)

            # Generate or retrieve session ID for provenance tracking
            session_id = getattr(request, 'session_id', '') or str(uuid.uuid4())
            collection = getattr(request, 'collection', 'default')

            if request.history:
                history = [
                    Action(
                        thought=h.thought,
                        name=h.action,
                        arguments=h.arguments,
                        observation=h.observation
                    )
                    for h in request.history
                ]
            else:
                history = []

            # Calculate iteration number (1-based)
            iteration_num = len(history) + 1
            session_uri = agent_session_uri(session_id)

            # On first iteration, emit session triples
            if iteration_num == 1:
                timestamp = datetime.utcnow().isoformat() + "Z"
                triples = set_graph(
                    agent_session_triples(session_uri, request.question, timestamp),
                    GRAPH_RETRIEVAL
                )
                await flow("explainability").send(Triples(
                    metadata=Metadata(
                        id=session_uri,
                        user=request.user,
                        collection=collection,
                    ),
                    triples=triples,
                ))
                logger.debug(f"Emitted session triples for {session_uri}")

                # Send explain event for session
                await respond(AgentResponse(
                    chunk_type="explain",
                    content="",
                    explain_id=session_uri,
                    explain_graph=GRAPH_RETRIEVAL,
                    explain_triples=triples,
                ))

            logger.info(f"Question: {request.question}")

            if len(history) >= self.max_iterations:
                raise RuntimeError("Too many agent iterations")

            logger.debug(f"History: {history}")

            thought_msg_id = agent_thought_uri(session_id, iteration_num)
            observation_msg_id = agent_observation_uri(session_id, iteration_num)

            async def think(x, is_final=False):

                logger.debug(f"Think: {x} (is_final={is_final})")

                if streaming:
                    r = AgentResponse(
                        chunk_type="thought",
                        content=x,
                        end_of_message=is_final,
                        end_of_dialog=False,
                        message_id=thought_msg_id,
                    )
                else:
                    r = AgentResponse(
                        chunk_type="thought",
                        content=x,
                        end_of_message=True,
                        end_of_dialog=False,
                        message_id=thought_msg_id,
                    )

                await respond(r)

            async def observe(x, is_final=False):

                logger.debug(f"Observe: {x} (is_final={is_final})")

                if streaming:
                    r = AgentResponse(
                        chunk_type="observation",
                        content=x,
                        end_of_message=is_final,
                        end_of_dialog=False,
                        message_id=observation_msg_id,
                    )
                else:
                    r = AgentResponse(
                        chunk_type="observation",
                        content=x,
                        end_of_message=True,
                        end_of_dialog=False,
                        message_id=observation_msg_id,
                    )

                await respond(r)

            answer_msg_id = agent_final_uri(session_id)

            async def answer(x):

                logger.debug(f"Answer: {x}")

                if streaming:
                    r = AgentResponse(
                        chunk_type="answer",
                        content=x,
                        end_of_message=False,
                        end_of_dialog=False,
                        message_id=answer_msg_id,
                    )
                else:
                    r = AgentResponse(
                        chunk_type="answer",
                        content=x,
                        end_of_message=True,
                        end_of_dialog=False,
                        message_id=answer_msg_id,
                    )

                await respond(r)

            # Apply tool filtering based on request groups and state
            filtered_tools = filter_tools_by_group_and_state(
                tools=self.agent.tools,
                requested_groups=getattr(request, 'group', None),
                current_state=getattr(request, 'state', None)
            )
            
            # Create temporary agent with filtered tools
            temp_agent = AgentManager(
                tools=filtered_tools,
                additional_context=self.agent.additional_context
            )
            
            logger.debug("Call React")

            # Create user-aware context wrapper that preserves the flow interface
            # but adds user information for tools that need it
            class UserAwareContext:
                def __init__(self, flow, user):
                    self._flow = flow
                    self._user = user
                    self.last_sub_explain_uri = None

                def __call__(self, service_name):
                    client = self._flow(service_name)
                    # For query clients that need user context, store it
                    if service_name in ("structured-query-request", "row-embeddings-query-request"):
                        client._current_user = self._user
                    return client

            # Callback: emit Analysis+ToolUse triples before tool executes
            async def on_action(act_decision):
                iter_uri = agent_iteration_uri(session_id, iteration_num)
                if iteration_num > 1:
                    iter_q_uri = None
                    iter_prev_uri = agent_observation_uri(session_id, iteration_num - 1)
                else:
                    iter_q_uri = session_uri
                    iter_prev_uri = None

                # Save thought to librarian
                t_doc_id = None
                if act_decision.thought:
                    t_doc_id = f"urn:trustgraph:agent:{session_id}/i{iteration_num}/thought"
                    try:
                        await self.save_answer_content(
                            doc_id=t_doc_id,
                            user=request.user,
                            content=act_decision.thought,
                            title=f"Agent Thought: {act_decision.name}",
                        )
                    except Exception as e:
                        logger.warning(f"Failed to save thought to librarian: {e}")
                        t_doc_id = None

                t_entity_uri = agent_thought_uri(session_id, iteration_num)

                iter_triples = set_graph(
                    agent_iteration_triples(
                        iter_uri,
                        question_uri=iter_q_uri,
                        previous_uri=iter_prev_uri,
                        action=act_decision.name,
                        arguments=act_decision.arguments,
                        thought_uri=t_entity_uri if t_doc_id else None,
                        thought_document_id=t_doc_id,
                    ),
                    GRAPH_RETRIEVAL
                )
                await flow("explainability").send(Triples(
                    metadata=Metadata(
                        id=iter_uri,
                        user=request.user,
                        collection=collection,
                    ),
                    triples=iter_triples,
                ))
                logger.debug(f"Emitted iteration triples for {iter_uri}")

                await respond(AgentResponse(
                    chunk_type="explain",
                    content="",
                    explain_id=iter_uri,
                    explain_graph=GRAPH_RETRIEVAL,
                    explain_triples=iter_triples,
                ))

            user_context = UserAwareContext(flow, request.user)

            act = await temp_agent.react(
                question = request.question,
                history = history,
                think = think,
                observe = observe,
                answer = answer,
                context = user_context,
                streaming = streaming,
                on_action = on_action,
            )

            logger.debug(f"Action: {act}")

            if isinstance(act, Final):

                logger.debug("Send final response...")

                if isinstance(act.final, str):
                    f = act.final
                else:
                    f = json.dumps(act.final)

                # Emit final answer provenance triples
                final_uri = agent_final_uri(session_id)
                # No iterations: link to question; otherwise: link to last observation
                if iteration_num > 1:
                    final_question_uri = None
                    final_previous_uri = agent_observation_uri(session_id, iteration_num - 1)
                else:
                    final_question_uri = session_uri
                    final_previous_uri = None

                # Save answer to librarian
                answer_doc_id = None
                if f:
                    answer_doc_id = f"urn:trustgraph:agent:{session_id}/answer"
                    try:
                        await self.save_answer_content(
                            doc_id=answer_doc_id,
                            user=request.user,
                            content=f,
                            title=f"Agent Answer: {request.question[:50]}...",
                        )
                        logger.debug(f"Saved answer to librarian: {answer_doc_id}")
                    except Exception as e:
                        logger.warning(f"Failed to save answer to librarian: {e}")
                        answer_doc_id = None  # Fall back to inline content

                final_triples = set_graph(
                    agent_final_triples(
                        final_uri,
                        question_uri=final_question_uri,
                        previous_uri=final_previous_uri,
                        document_id=answer_doc_id,
                    ),
                    GRAPH_RETRIEVAL
                )
                await flow("explainability").send(Triples(
                    metadata=Metadata(
                        id=final_uri,
                        user=request.user,
                        collection=collection,
                    ),
                    triples=final_triples,
                ))
                logger.debug(f"Emitted final triples for {final_uri}")

                # Send explain event for conclusion
                await respond(AgentResponse(
                    chunk_type="explain",
                    content="",
                    explain_id=final_uri,
                    explain_graph=GRAPH_RETRIEVAL,
                    explain_triples=final_triples,
                ))

                if streaming:
                    # End-of-dialog marker — answer chunks already sent via callback
                    r = AgentResponse(
                        chunk_type="answer",
                        content="",
                        end_of_message=True,
                        end_of_dialog=True,
                        message_id=answer_msg_id,
                    )
                else:
                    r = AgentResponse(
                        chunk_type="answer",
                        content=f,
                        end_of_message=True,
                        end_of_dialog=True,
                        message_id=answer_msg_id,
                    )

                await respond(r)

                logger.debug("Done.")

                return

            logger.debug("Send next...")

            # Emit standalone observation provenance (iteration was emitted in on_action)
            iteration_uri = agent_iteration_uri(session_id, iteration_num)
            observation_entity_uri = agent_observation_uri(session_id, iteration_num)

            # Derive from last sub-trace entity if available, else iteration
            obs_parent_uri = iteration_uri
            if user_context.last_sub_explain_uri:
                obs_parent_uri = user_context.last_sub_explain_uri

            observation_doc_id = None
            if act.observation:
                observation_doc_id = f"urn:trustgraph:agent:{session_id}/i{iteration_num}/observation"
                try:
                    await self.save_answer_content(
                        doc_id=observation_doc_id,
                        user=request.user,
                        content=act.observation,
                        title=f"Agent Observation",
                    )
                    logger.debug(f"Saved observation to librarian: {observation_doc_id}")
                except Exception as e:
                    logger.warning(f"Failed to save observation to librarian: {e}")
                    observation_doc_id = None

            obs_triples = set_graph(
                agent_observation_triples(
                    observation_entity_uri,
                    obs_parent_uri,
                    document_id=observation_doc_id,
                ),
                GRAPH_RETRIEVAL
            )
            await flow("explainability").send(Triples(
                metadata=Metadata(
                    id=observation_entity_uri,
                    user=request.user,
                    collection=collection,
                ),
                triples=obs_triples,
            ))
            logger.debug(f"Emitted observation triples for {observation_entity_uri}")

            # Send explain event for observation
            await respond(AgentResponse(
                chunk_type="explain",
                content="",
                explain_id=observation_entity_uri,
                explain_graph=GRAPH_RETRIEVAL,
                explain_triples=obs_triples,
            ))

            history.append(act)

            # Handle state transitions if tool execution was successful
            next_state = request.state
            if act.name in filtered_tools:
                executed_tool = filtered_tools[act.name]
                next_state = get_next_state(executed_tool, request.state or "undefined")

            r = AgentRequest(
                question=request.question,
                state=next_state,
                group=getattr(request, 'group', []),
                history=[
                    AgentStep(
                        thought=h.thought,
                        action=h.name,
                        arguments={k: str(v) for k, v in h.arguments.items()},
                        observation=h.observation
                    )
                    for h in history
                ],
                user=request.user,
                collection=collection,
                streaming=streaming,
                session_id=session_id,  # Pass session_id for provenance continuity
            )

            await next(r)

            logger.debug("React agent processing complete")

            return

        except Exception as e:

            logger.error(f"agent_request Exception: {e}", exc_info=True)

            logger.debug("Send error response...")

            error_obj = Error(
                type = "agent-error",
                message = str(e),
            )

            # Check if streaming was enabled (may not be set if error occurred early)
            streaming = getattr(request, 'streaming', False) if 'request' in locals() else False

            r = AgentResponse(
                chunk_type="error",
                content=str(e),
                end_of_message=True,
                end_of_dialog=True,
                error=error_obj,
            )

            await respond(r)

    @staticmethod
    def add_args(parser):

        AgentService.add_args(parser)

        parser.add_argument(
            '--max-iterations',
            default=default_max_iterations,
            help=f'Maximum number of react iterations (default: {default_max_iterations})',
        )

        parser.add_argument(
            '--config-type',
            default="agent",
            help=f'Configuration key for prompts (default: agent)',
        )

def run():
    Processor.launch(default_ident, __doc__)

