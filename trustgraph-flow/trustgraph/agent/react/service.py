"""
Simple agent infrastructure broadly implements the ReAct flow.
"""

import json
import re
import sys
import functools

from ... base import AgentService, TextCompletionClientSpec, PromptClientSpec
from ... base import GraphRagClientSpec, ToolClientSpec

from ... schema import AgentRequest, AgentResponse, AgentStep, Error

from . tools import KnowledgeQueryImpl, TextCompletionImpl, McpToolImpl, PromptImpl
from . agent_manager import AgentManager

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
            tools=[],
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

    async def on_tools_config(self, config, version):

        print("Loading configuration version", version)

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
                        impl = functools.partial(
                            McpToolImpl, 
                            mcp_tool_id=data.get("mcp-tool")
                        )
                        arguments = McpToolImpl.get_arguments()
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
                    else:
                        raise RuntimeError(
                            f"Tool type {impl_id} not known"
                        )
                    
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

            print(f"Loaded {len(tools)} tools", flush=True)
            print("Tool configuration reloaded.", flush=True)

        except Exception as e:

            print("on_tools_config Exception:", e, flush=True)
            print("Configuration reload failed", flush=True)

    async def agent_request(self, request, respond, next, flow):

        try:

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

            print(f"Question: {request.question}", flush=True)

            if len(history) >= self.max_iterations:
                raise RuntimeError("Too many agent iterations")

            print(f"History: {history}", flush=True)

            async def think(x):

                print(f"Think: {x}", flush=True)

                r = AgentResponse(
                    answer=None,
                    error=None,
                    thought=x,
                    observation=None,
                )

                await respond(r)

            async def observe(x):

                print(f"Observe: {x}", flush=True)

                r = AgentResponse(
                    answer=None,
                    error=None,
                    thought=None,
                    observation=x,
                )

                await respond(r)

            print("Call React", flush=True)

            act = await self.agent.react(
                question = request.question,
                history = history,
                think = think,
                observe = observe,
                context = flow,
            )

            print(f"Action: {act}", flush=True)

            if isinstance(act, Final):

                print("Send final response...", flush=True)

                if isinstance(act.final, str):
                    f = act.final
                else:
                    f = json.dumps(act.final)

                r = AgentResponse(
                    answer=act.final,
                    error=None,
                    thought=None,
                )

                await respond(r)

                print("Done.", flush=True)

                return

            print("Send next...", flush=True)

            history.append(act)

            r = AgentRequest(
                question=request.question,
                plan=request.plan,
                state=request.state,
                history=[
                    AgentStep(
                        thought=h.thought,
                        action=h.name,
                        arguments=h.arguments,
                        observation=h.observation
                    )
                    for h in history
                ]
            )

            await next(r)

            print("Done.", flush=True)

            return

        except Exception as e:

            print(f"agent_request Exception: {e}")

            print("Send error response...", flush=True)

            r = AgentResponse(
                error=Error(
                    type = "agent-error",
                    message = str(e),
                ),
                response=None,
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

