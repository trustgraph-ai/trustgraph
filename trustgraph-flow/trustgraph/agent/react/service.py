"""
Simple agent infrastructure broadly implements the ReAct flow.
"""

import json
import re

from pulsar.schema import JsonSchema

from ... base import ConsumerProducer
from ... schema import Error
from ... schema import AgentRequest, AgentResponse, AgentStep
from ... schema import agent_request_queue, agent_response_queue
from ... schema import prompt_request_queue as pr_request_queue
from ... schema import prompt_response_queue as pr_response_queue
from ... schema import text_completion_request_queue as tc_request_queue
from ... schema import text_completion_response_queue as tc_response_queue
from ... schema import graph_rag_request_queue as gr_request_queue
from ... schema import graph_rag_response_queue as gr_response_queue
from ... clients.prompt_client import PromptClient
from ... clients.llm_client import LlmClient
from ... clients.graph_rag_client import GraphRagClient

from . tools import CatsKb, ShuttleKb, Compute
from . agent_manager import AgentManager
from . types import Final, Action

module = ".".join(__name__.split(".")[1:-1])

default_input_queue = agent_request_queue
default_output_queue = agent_response_queue
default_subscriber = module

class Processor(ConsumerProducer):

    def __init__(self, **params):

        input_queue = params.get("input_queue", default_input_queue)
        output_queue = params.get("output_queue", default_output_queue)
        subscriber = params.get("subscriber", default_subscriber)
        prompt_request_queue = params.get(
            "prompt_request_queue", pr_request_queue
        )
        prompt_response_queue = params.get(
            "prompt_response_queue", pr_response_queue
        )
        text_completion_request_queue = params.get(
            "text_completion_request_queue", tc_request_queue
        )
        text_completion_response_queue = params.get(
            "text_completion_response_queue", tc_response_queue
        )
        graph_rag_request_queue = params.get(
            "graph_rag_request_queue", gr_request_queue
        )
        graph_rag_response_queue = params.get(
            "graph_rag_response_queue", gr_response_queue
        )

        super(Processor, self).__init__(
            **params | {
                "input_queue": input_queue,
                "output_queue": output_queue,
                "subscriber": subscriber,
                "input_schema": AgentRequest,
                "output_schema": AgentResponse,
                "prompt_request_queue": prompt_request_queue,
                "prompt_response_queue": prompt_response_queue,
                "text_completion_request_queue": tc_request_queue,
                "text_completion_response_queue": tc_response_queue,
                "graph_rag_request_queue": gr_request_queue,
                "graph_rag_response_queue": gr_response_queue,
            }
        )

        self.prompt = PromptClient(
            subscriber=subscriber,
            input_queue=prompt_request_queue,
            output_queue=prompt_response_queue,
            pulsar_host = self.pulsar_host
        )

        self.llm = LlmClient(
            subscriber=subscriber,
            input_queue=text_completion_request_queue,
            output_queue=text_completion_response_queue,
            pulsar_host = self.pulsar_host
        )

        self.graph_rag = GraphRagClient(
            subscriber=subscriber,
            input_queue=graph_rag_request_queue,
            output_queue=graph_rag_response_queue,
            pulsar_host = self.pulsar_host
        )

        # Need to be able to feed requests to myself
        self.recursive_input = self.client.create_producer(
            topic=input_queue,
            schema=JsonSchema(AgentRequest),
        )

        tools = [
            CatsKb(self), ShuttleKb(self), Compute(self),
        ]

        self.agent = AgentManager(self, tools)

    def parse_json(self, text):
        json_match = re.search(r'```(?:json)?(.*?)```', text, re.DOTALL)
    
        if json_match:
            json_str = json_match.group(1).strip()
        else:
            # If no delimiters, assume the entire output is JSON
            json_str = text.strip()

        return json.loads(json_str)

    def handle(self, msg):

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

            if len(history) > 10:
                raise RuntimeError("Too many agent iterations")

            print(f"History: {history}", flush=True)

            def think(x):

                print(f"Think: {x}", flush=True)

                r = AgentResponse(
                    answer=None,
                    error=None,
                    thought=x,
                    observation=None,
                )

                self.producer.send(r, properties={"id": id})

            def observe(x):

                print(f"Observe: {x}", flush=True)

                r = AgentResponse(
                    answer=None,
                    error=None,
                    thought=None,
                    observation=x,
                )

                self.producer.send(r, properties={"id": id})

            act = self.agent.react(v.question, history, think, observe)

            print(f"Action: {act}", flush=True)

            print("Send response...", flush=True)

            if type(act) == Final:

                r = AgentResponse(
                    answer=act.final,
                    error=None,
                    thought=None,
                )

                self.producer.send(r, properties={"id": id})

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

            self.producer.send(r, properties={"id": id})

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
            '--text-completion-request-queue',
            default=tc_request_queue,
            help=f'Text completion request queue (default: {tc_request_queue})',
        )

        parser.add_argument(
            '--text-completion-response-queue',
            default=tc_response_queue,
            help=f'Text completion response queue (default: {tc_response_queue})',
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

def run():

    Processor.start(module, __doc__)

