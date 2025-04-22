"""
Simple agent infrastructure broadly implements the ReAct flow.
"""

import json
import re
import sys

from ... base import AgentService, TextCompletionClientSpec, PromptClientSpec
from ... base import GraphRagClientSpec

from ... schema import AgentRequest, AgentResponse, AgentStep, Error

from . tools import KnowledgeQueryImpl, TextCompletionImpl
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

    async def on_tools_config(self, config, version):

        print("Loading configuration version", version)

        if self.config_key not in config:
            print(f"No key {self.config_key} in config", flush=True)
            return

        config = config[self.config_key]

        try:

            # This is some extra stuff to put in the prompt
            additional = config.get("additional-context", None)

            ix = json.loads(config["tool-index"])

            tools = {}

            for k in ix:

                pc = config[f"tool.{k}"]
                data = json.loads(pc)

                arguments = {
                    v.get("name"): Argument(
                        name = v.get("name"),
                        type = v.get("type"),
                        description = v.get("description")
                    )
                    for v in data["arguments"]
                }

                impl_id = data.get("type")

                if impl_id == "knowledge-query":
                    impl = KnowledgeQueryImpl
                elif impl_id == "text-completion":
                    impl = TextCompletionImpl
                else:
                    raise RuntimeError(
                        f"Tool-kind {impl_id} not known"
                    )

                tools[data.get("name")] = Tool(
                    name = data.get("name"),
                    description = data.get("description"),
                    implementation = impl,
                    config=data.get("config", {}),
                    arguments = arguments,
                )

            self.agent = AgentManager(
                tools=tools,
                additional_context=additional
            )

            print("Prompt configuration reloaded.", flush=True)

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

