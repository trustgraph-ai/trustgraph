"""
Agent orchestrator service — multi-pattern drop-in replacement for
agent-manager-react.

Uses the same service identity and Pulsar queues. Adds meta-routing
to select between ReactPattern, PlanThenExecutePattern, and
SupervisorPattern at runtime.
"""

import asyncio
import base64
import json
import functools
import logging
import uuid
from datetime import datetime

from ... base import AgentService, TextCompletionClientSpec, PromptClientSpec
from ... base import GraphRagClientSpec, ToolClientSpec, StructuredQueryClientSpec
from ... base import RowEmbeddingsQueryClientSpec, EmbeddingsClientSpec
from ... base import ProducerSpec
from ... base import Consumer, Producer
from ... base import ConsumerMetrics, ProducerMetrics

from ... schema import AgentRequest, AgentResponse, AgentStep, Error
from ..orchestrator.pattern_base import UsageTracker, PatternBase
from ... schema import Triples, Metadata
from ... schema import LibrarianRequest, LibrarianResponse, DocumentMetadata
from ... schema import librarian_request_queue, librarian_response_queue

from trustgraph.provenance import (
    agent_session_uri,
    GRAPH_RETRIEVAL,
)

from ..react.tools import (
    KnowledgeQueryImpl, TextCompletionImpl, McpToolImpl, PromptImpl,
    StructuredQueryImpl, RowEmbeddingsQueryImpl, ToolServiceImpl,
)
from ..react.agent_manager import AgentManager
from ..tool_filter import validate_tool_config
from ..react.types import Final, Action, Tool, Argument

from . meta_router import MetaRouter
from . pattern_base import PatternBase, UserAwareContext
from . react_pattern import ReactPattern
from . plan_pattern import PlanThenExecutePattern
from . supervisor_pattern import SupervisorPattern
from . aggregator import Aggregator

logger = logging.getLogger(__name__)

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

        self.tool_service_clients = {}

        # Patterns
        self.react_pattern = ReactPattern(self)
        self.plan_pattern = PlanThenExecutePattern(self)
        self.supervisor_pattern = SupervisorPattern(self)

        # Aggregator for supervisor fan-in
        self.aggregator = Aggregator()

        # Meta-router (initialised on first config load)
        self.meta_router = None

        self.register_config_handler(
            self.on_tools_config, types=["tool", "tool-service"]
        )

        self.register_specification(
            TextCompletionClientSpec(
                request_name="text-completion-request",
                response_name="text-completion-response",
            )
        )

        self.register_specification(
            GraphRagClientSpec(
                request_name="graph-rag-request",
                response_name="graph-rag-response",
            )
        )

        self.register_specification(
            PromptClientSpec(
                request_name="prompt-request",
                response_name="prompt-response",
            )
        )

        self.register_specification(
            ToolClientSpec(
                request_name="mcp-tool-request",
                response_name="mcp-tool-response",
            )
        )

        self.register_specification(
            StructuredQueryClientSpec(
                request_name="structured-query-request",
                response_name="structured-query-response",
            )
        )

        self.register_specification(
            EmbeddingsClientSpec(
                request_name="embeddings-request",
                response_name="embeddings-response",
            )
        )

        self.register_specification(
            RowEmbeddingsQueryClientSpec(
                request_name="row-embeddings-query-request",
                response_name="row-embeddings-query-response",
            )
        )

        # Explainability producer
        self.register_specification(
            ProducerSpec(
                name="explainability",
                schema=Triples,
            )
        )

        # Librarian client
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

        self.pending_librarian_requests = {}

    async def start(self):
        await super(Processor, self).start()
        await self.librarian_request_producer.start()
        await self.librarian_response_consumer.start()

    async def on_librarian_response(self, msg, consumer, flow):
        response = msg.value()
        request_id = msg.properties().get("id")

        if request_id in self.pending_librarian_requests:
            future = self.pending_librarian_requests.pop(request_id)
            future.set_result(response)

    async def save_answer_content(self, doc_id, user, content, title=None,
                                  timeout=120):
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

        future = asyncio.get_event_loop().create_future()
        self.pending_librarian_requests[request_id] = future

        try:
            await self.librarian_request_producer.send(
                request, properties={"id": request_id}
            )
            response = await asyncio.wait_for(future, timeout=timeout)

            if response.error:
                raise RuntimeError(
                    f"Librarian error saving answer: "
                    f"{response.error.type}: {response.error.message}"
                )
            return doc_id

        except asyncio.TimeoutError:
            self.pending_librarian_requests.pop(request_id, None)
            raise RuntimeError(f"Timeout saving answer document {doc_id}")

    def provenance_session_uri(self, session_id):
        return agent_session_uri(session_id)

    async def on_tools_config(self, config, version):

        logger.info(f"Loading configuration version {version}")

        try:
            tools = {}

            # Load tool-service configurations
            tool_services = {}
            if "tool-service" in config:
                for service_id, service_value in config["tool-service"].items():
                    service_data = json.loads(service_value)
                    tool_services[service_id] = service_data
                    logger.debug(f"Loaded tool-service config: {service_id}")

            logger.info(
                f"Loaded {len(tool_services)} tool-service configurations"
            )

            # Load tool configurations
            if "tool" in config:
                for tool_id, tool_value in config["tool"].items():
                    data = json.loads(tool_value)
                    impl_id = data.get("type")
                    name = data.get("name")

                    if impl_id == "knowledge-query":
                        impl = functools.partial(
                            KnowledgeQueryImpl,
                            collection=data.get("collection"),
                        )
                        arguments = KnowledgeQueryImpl.get_arguments()
                    elif impl_id == "text-completion":
                        impl = TextCompletionImpl
                        arguments = TextCompletionImpl.get_arguments()
                    elif impl_id == "mcp-tool":
                        config_args = data.get("arguments", [])
                        arguments = [
                            Argument(
                                name=arg.get("name"),
                                type=arg.get("type"),
                                description=arg.get("description"),
                            )
                            for arg in config_args
                        ]
                        impl = functools.partial(
                            McpToolImpl,
                            mcp_tool_id=data.get("mcp-tool"),
                            arguments=arguments,
                        )
                    elif impl_id == "prompt":
                        config_args = data.get("arguments", [])
                        arguments = [
                            Argument(
                                name=arg.get("name"),
                                type=arg.get("type"),
                                description=arg.get("description"),
                            )
                            for arg in config_args
                        ]
                        impl = functools.partial(
                            PromptImpl,
                            template_id=data.get("template"),
                            arguments=arguments,
                        )
                    elif impl_id == "structured-query":
                        impl = functools.partial(
                            StructuredQueryImpl,
                            collection=data.get("collection"),
                            user=None,
                        )
                        arguments = StructuredQueryImpl.get_arguments()
                    elif impl_id == "row-embeddings-query":
                        impl = functools.partial(
                            RowEmbeddingsQueryImpl,
                            schema_name=data.get("schema-name"),
                            collection=data.get("collection"),
                            user=None,
                            index_name=data.get("index-name"),
                            limit=int(data.get("limit", 10)),
                        )
                        arguments = RowEmbeddingsQueryImpl.get_arguments()
                    elif impl_id == "tool-service":
                        service_ref = data.get("service")
                        if not service_ref:
                            raise RuntimeError(
                                f"Tool {name} has type 'tool-service' "
                                f"but no 'service' reference"
                            )
                        if service_ref not in tool_services:
                            raise RuntimeError(
                                f"Tool {name} references unknown "
                                f"tool-service '{service_ref}'"
                            )

                        service_config = tool_services[service_ref]
                        request_queue = service_config.get("request-queue")
                        response_queue = service_config.get("response-queue")
                        if not request_queue or not response_queue:
                            raise RuntimeError(
                                f"Tool-service '{service_ref}' must define "
                                f"'request-queue' and 'response-queue'"
                            )

                        config_params = service_config.get("config-params", [])
                        config_values = {}
                        for param in config_params:
                            param_name = (
                                param.get("name")
                                if isinstance(param, dict) else param
                            )
                            if param_name in data:
                                config_values[param_name] = data[param_name]
                            elif (
                                isinstance(param, dict)
                                and param.get("required", False)
                            ):
                                raise RuntimeError(
                                    f"Tool {name} missing required config "
                                    f"param '{param_name}'"
                                )

                        config_args = data.get("arguments", [])
                        arguments = [
                            Argument(
                                name=arg.get("name"),
                                type=arg.get("type"),
                                description=arg.get("description"),
                            )
                            for arg in config_args
                        ]

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

                    validate_tool_config(data)

                    tools[name] = Tool(
                        name=name,
                        description=data.get("description"),
                        implementation=impl,
                        config=data,
                        arguments=arguments,
                    )

            # Load additional context from agent config
            additional = None
            if self.config_key in config:
                agent_config = config[self.config_key]
                additional = agent_config.get("additional-context", None)

            self.agent = AgentManager(
                tools=tools,
                additional_context=additional,
            )

            # Re-initialise meta-router with config
            self.meta_router = MetaRouter(config=config)

            logger.info(f"Loaded {len(tools)} tools")

        except Exception as e:
            logger.error(
                f"on_tools_config Exception: {e}", exc_info=True
            )
            logger.error("Configuration reload failed")

    async def _handle_subagent_completion(self, request, respond, next, flow):
        """Handle a subagent completion by feeding it to the aggregator."""

        correlation_id = request.correlation_id
        subagent_goal = getattr(request, 'subagent_goal', '')
        parent_session_id = getattr(request, 'parent_session_id', '')

        # Extract the answer from the completion step
        answer_text = ""
        for step in request.history:
            if getattr(step, 'step_type', '') == 'subagent-completion':
                answer_text = step.observation
                break

        logger.debug(
            f"Received subagent completion: "
            f"correlation={correlation_id}, goal={subagent_goal}"
        )

        all_done = self.aggregator.record_completion(
            correlation_id, subagent_goal, answer_text
        )

        if all_done is None:
            logger.warning(
                f"Unknown correlation_id {correlation_id} — "
                f"possibly timed out or duplicate"
            )
            return

        # Emit finding provenance for this subagent
        template = self.aggregator.get_original_request(correlation_id)
        if template and parent_session_id:
            entry = self.aggregator.correlations.get(correlation_id)
            finding_index = len(entry["results"]) - 1 if entry else 0
            collection = getattr(template, 'collection', 'default')

            subagent_session_id = getattr(request, 'session_id', '')

            await self.supervisor_pattern.emit_finding_triples(
                flow, parent_session_id, finding_index,
                subagent_goal, answer_text,
                template.user, collection,
                respond, template.streaming,
                subagent_session_id=subagent_session_id,
            )

        if all_done:
            logger.info(
                f"All subagents complete for {correlation_id}, "
                f"dispatching synthesis"
            )

            if template is None:
                logger.error(
                    f"No template for correlation {correlation_id}"
                )
                return

            synthesis_request = self.aggregator.build_synthesis_request(
                correlation_id,
                original_question=template.question,
                user=template.user,
                collection=getattr(template, 'collection', 'default'),
            )

            await next(synthesis_request)

    async def agent_request(self, request, respond, next, flow):

        usage = UsageTracker()

        try:

            # Intercept subagent completion messages
            correlation_id = getattr(request, 'correlation_id', '')
            if correlation_id and request.history:
                is_completion = any(
                    getattr(h, 'step_type', '') == 'subagent-completion'
                    for h in request.history
                )
                if is_completion:
                    await self._handle_subagent_completion(
                        request, respond, next, flow
                    )
                    return

            pattern = getattr(request, 'pattern', '') or ''

            # If no pattern set and this is the first iteration, route
            if not pattern and not request.history:
                context = UserAwareContext(flow, request.user)

                if self.meta_router:
                    pattern, task_type, framing = await self.meta_router.route(
                        request.question, context, usage=usage,
                    )
                else:
                    pattern = "react"
                    task_type = "general"
                    framing = ""

                # Update request with routing decision
                request.pattern = pattern
                request.task_type = task_type
                request.framing = framing

                logger.info(
                    f"Routed to pattern={pattern}, "
                    f"task_type={task_type}"
                )

            # Dispatch to the selected pattern
            selected = self.react_pattern
            if pattern == "plan-then-execute":
                selected = self.plan_pattern
            elif pattern == "supervisor":
                selected = self.supervisor_pattern

            # Emit pattern decision provenance on first iteration
            pattern_decision_uri = None
            if not request.history and pattern:
                session_id = getattr(request, 'session_id', '')
                if session_id:
                    session_uri = self.provenance_session_uri(session_id)
                    pattern_decision_uri = \
                        await selected.emit_pattern_decision_triples(
                            flow, session_id, session_uri,
                            pattern, getattr(request, 'task_type', ''),
                            request.user,
                            getattr(request, 'collection', 'default'),
                            respond,
                        )

            await selected.iterate(
                request, respond, next, flow, usage=usage,
                pattern_decision_uri=pattern_decision_uri,
            )

        except Exception as e:

            logger.error(
                f"agent_request Exception: {e}", exc_info=True
            )

            logger.debug("Send error response...")

            error_obj = Error(
                type="agent-error",
                message=str(e),
            )

            r = AgentResponse(
                message_type="error",
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
            help=f'Maximum number of react iterations '
                 f'(default: {default_max_iterations})',
        )

        parser.add_argument(
            '--config-type',
            default="agent",
            help='Configuration key for prompts (default: agent)',
        )


def run():
    Processor.launch(default_ident, __doc__)
