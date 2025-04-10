"""
Simple agent infrastructure broadly implements the ReAct flow.
"""

import json
import re
import sys

from pulsar.schema import JsonSchema

from ... base import ConsumerProducer
from ... schema import Error
from ... schema import AgentRequest, AgentResponse, AgentStep
from ... schema import agent_request_queue, agent_response_queue
from ... schema import prompt_request_queue as pr_request_queue
from ... schema import prompt_response_queue as pr_response_queue
from ... schema import graph_rag_request_queue as gr_request_queue
from ... schema import graph_rag_response_queue as gr_response_queue
from ... clients.prompt_client import PromptClient
from ... clients.llm_client import LlmClient
from ... clients.graph_rag_client import GraphRagClient

from . tools import KnowledgeQueryImpl, TextCompletionImpl
from . agent_manager import AgentManager

from . types import Final, Action, Tool, Argument

module = "agent"

default_input_queue = agent_request_queue
default_output_queue = agent_response_queue
default_subscriber = module
default_max_iterations = 15

class Processor(ConsumerProducer):

    def __init__(self, **params):

        self.max_iterations = int(
            params.get("max_iterations", default_max_iterations)
        )

        tools = {}

        input_queue = params.get("input_queue", default_input_queue)
        output_queue = params.get("output_queue", default_output_queue)
        subscriber = params.get("subscriber", default_subscriber)
        prompt_request_queue = params.get(
            "prompt_request_queue", pr_request_queue
        )
        prompt_response_queue = params.get(
            "prompt_response_queue", pr_response_queue
        )
        graph_rag_request_queue = params.get(
            "graph_rag_request_queue", gr_request_queue
        )
        graph_rag_response_queue = params.get(
            "graph_rag_response_queue", gr_response_queue
        )

        self.config_key = params.get("config_type", "agent")

        super(Processor, self).__init__(
            **params | {
                "input_queue": input_queue,
                "output_queue": output_queue,
                "subscriber": subscriber,
                "input_schema": AgentRequest,
                "output_schema": AgentResponse,
                "prompt_request_queue": prompt_request_queue,
                "prompt_response_queue": prompt_response_queue,
                "graph_rag_request_queue": gr_request_queue,
                "graph_rag_response_queue": gr_response_queue,
            }
        )

        self.prompt = PromptClient(
            subscriber=subscriber,
            input_queue=prompt_request_queue,
            output_queue=prompt_response_queue,
            pulsar_host = self.pulsar_host,
            pulsar_api_key=self.pulsar_api_key,
        )

        self.graph_rag = GraphRagClient(
            subscriber=subscriber,
            input_queue=graph_rag_request_queue,
            output_queue=graph_rag_response_queue,
            pulsar_host = self.pulsar_host,
            pulsar_api_key=self.pulsar_api_key,
        )

        # Need to be able to feed requests to myself
        self.recursive_input = self.client.create_producer(
            topic=input_queue,
            schema=JsonSchema(AgentRequest),
        )

        self.agent = AgentManager(
            context=self,
            tools=[],
            additional_context="",
        )

        self.config_handlers.append(self.on_config)

    async def on_config(self, version, config):

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
                    impl = KnowledgeQueryImpl(self)
                elif impl_id == "text-completion":
                    impl = TextCompletionImpl(self)
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
                context=self,
                tools=tools,
                additional_context=additional
            )

            print("Prompt configuration reloaded.", flush=True)

        except Exception as e:

            print("Exception:", e, flush=True)
            print("Configuration reload failed", flush=True)

    async def handle(self, msg):

        try:

            v = msg.value()

            # Sender-produced ID
            id = msg.properties()["id"]

            if v.history:
                history = [
                    Action(
                        thought=h.thought,
                        name=h.action,
                        arguments=h.arguments,
                        observation=h.observation
                    )
                    for h in v.history
                ]
            else:
                history = []

            print(f"Question: {v.question}", flush=True)

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

                await self.send(r, properties={"id": id})

            async def observe(x):

                print(f"Observe: {x}", flush=True)

                r = AgentResponse(
                    answer=None,
                    error=None,
                    thought=None,
                    observation=x,
                )

                await self.send(r, properties={"id": id})

            act = await self.agent.react(v.question, history, think, observe)

            print(f"Action: {act}", flush=True)

            print("Send response...", flush=True)

            if type(act) == Final:

                r = AgentResponse(
                    answer=act.final,
                    error=None,
                    thought=None,
                )

                await self.send(r, properties={"id": id})

                print("Done.", flush=True)

                return

            history.append(act)

            r = AgentRequest(
                question=v.question,
                plan=v.plan,
                state=v.state,
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

            self.recursive_input.send(r, properties={"id": id})

            print("Done.", flush=True)

            return

        except Exception as e:

            print(f"Exception: {e}")

            print("Send error response...", flush=True)

            r = AgentResponse(
                error=Error(
                    type = "agent-error",
                    message = str(e),
                ),
                response=None,
            )

            await self.send(r, properties={"id": id})

    @staticmethod
    def add_args(parser):

        ConsumerProducer.add_args(
            parser, default_input_queue, default_subscriber,
            default_output_queue,
        )

        parser.add_argument(
            '--prompt-request-queue',
            default=pr_request_queue,
            help=f'Prompt request queue (default: {pr_request_queue})',
        )

        parser.add_argument(
            '--prompt-response-queue',
            default=pr_response_queue,
            help=f'Prompt response queue (default: {pr_response_queue})',
        )

        parser.add_argument(
            '--graph-rag-request-queue',
            default=gr_request_queue,
            help=f'Graph RAG request queue (default: {gr_request_queue})',
        )

        parser.add_argument(
            '--graph-rag-response-queue',
            default=gr_response_queue,
            help=f'Graph RAG response queue (default: {gr_response_queue})',
        )

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

    Processor.launch(module, __doc__)

