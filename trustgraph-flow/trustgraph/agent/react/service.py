"""
Simple agent infrastructure broadly implements the ReAct flow.
"""

import json
import re
import sys
import functools
import logging

# Module logger
logger = logging.getLogger(__name__)

from ... base import AgentService, TextCompletionClientSpec, PromptClientSpec
from ... base import GraphRagClientSpec, ToolClientSpec, StructuredQueryClientSpec

from ... schema import AgentRequest, AgentResponse, AgentStep, Error

from . tools import KnowledgeQueryImpl, TextCompletionImpl, McpToolImpl, PromptImpl, StructuredQueryImpl
from . agent_manager import AgentManager
from ..tool_filter import validate_tool_config, filter_tools_by_group_and_state, get_next_state

from . types import Final, Action, Tool, Argument

default_ident = "agent-manager"
default_max_iterations = 10

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

        self.config_handlers.append(self.on_tools_config)

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

    async def on_tools_config(self, config, version):

        logger.info(f"Loading configuration version {version}")

        try:

            tools = {}

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

            logger.info(f"Question: {request.question}")

            if len(history) >= self.max_iterations:
                raise RuntimeError("Too many agent iterations")

            logger.debug(f"History: {history}")

            async def think(x, is_final=False):

                logger.debug(f"Think: {x} (is_final={is_final})")

                if streaming:
                    # Streaming format
                    r = AgentResponse(
                        chunk_type="thought",
                        content=x,
                        end_of_message=is_final,
                        end_of_dialog=False,
                        # Legacy fields for backward compatibility
                        answer=None,
                        error=None,
                        thought=x,
                        observation=None,
                    )
                else:
                    # Non-streaming format
                    r = AgentResponse(
                        answer=None,
                        error=None,
                        thought=x,
                        observation=None,
                        end_of_message=True,
                        end_of_dialog=False,
                    )

                await respond(r)

            async def observe(x, is_final=False):

                logger.debug(f"Observe: {x} (is_final={is_final})")

                if streaming:
                    # Streaming format
                    r = AgentResponse(
                        chunk_type="observation",
                        content=x,
                        end_of_message=is_final,
                        end_of_dialog=False,
                        # Legacy fields for backward compatibility
                        answer=None,
                        error=None,
                        thought=None,
                        observation=x,
                    )
                else:
                    # Non-streaming format
                    r = AgentResponse(
                        answer=None,
                        error=None,
                        thought=None,
                        observation=x,
                        end_of_message=True,
                        end_of_dialog=False,
                    )

                await respond(r)

            async def answer(x):

                logger.debug(f"Answer: {x}")

                if streaming:
                    # Streaming format
                    r = AgentResponse(
                        chunk_type="answer",
                        content=x,
                        end_of_message=False,  # More chunks may follow
                        end_of_dialog=False,
                        # Legacy fields for backward compatibility
                        answer=None,
                        error=None,
                        thought=None,
                        observation=None,
                    )
                else:
                    # Non-streaming format - shouldn't normally be called
                    r = AgentResponse(
                        answer=x,
                        error=None,
                        thought=None,
                        observation=None,
                        end_of_message=True,
                        end_of_dialog=False,
                    )

                await respond(r)

            # Apply tool filtering based on request groups and state
            filtered_tools = filter_tools_by_group_and_state(
                tools=self.agent.tools,
                requested_groups=getattr(request, 'group', None),
                current_state=getattr(request, 'state', None)
            )
            
            logger.info(f"Filtered from {len(self.agent.tools)} to {len(filtered_tools)} available tools")
            
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
                
                def __call__(self, service_name):
                    client = self._flow(service_name)
                    # For structured query clients, store user context
                    if service_name == "structured-query-request":
                        client._current_user = self._user
                    return client

            act = await temp_agent.react(
                question = request.question,
                history = history,
                think = think,
                observe = observe,
                answer = answer,
                context = UserAwareContext(flow, request.user),
                streaming = streaming,
            )

            logger.debug(f"Action: {act}")

            if isinstance(act, Final):

                logger.debug("Send final response...")

                if isinstance(act.final, str):
                    f = act.final
                else:
                    f = json.dumps(act.final)

                if streaming:
                    # Streaming format - send end-of-dialog marker
                    # Answer chunks were already sent via answer() callback during parsing
                    r = AgentResponse(
                        chunk_type="answer",
                        content="",  # Empty content, just marking end of dialog
                        end_of_message=True,
                        end_of_dialog=True,
                        # Legacy fields set to None - answer already sent via streaming chunks
                        answer=None,
                        error=None,
                        thought=None,
                    )
                else:
                    # Non-streaming format - send complete answer
                    r = AgentResponse(
                        answer=act.final,
                        error=None,
                        thought=None,
                        end_of_message=True,
                        end_of_dialog=True,
                    )

                await respond(r)

                logger.debug("Done.")

                return

            logger.debug("Send next...")

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
                streaming=streaming,
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

            if streaming:
                # Streaming format
                r = AgentResponse(
                    chunk_type="error",
                    content=str(e),
                    end_of_message=True,
                    end_of_dialog=True,
                    # Legacy fields for backward compatibility
                    error=error_obj,
                )
            else:
                # Legacy format
                r = AgentResponse(
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

