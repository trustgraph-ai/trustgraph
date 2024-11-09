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
from ... clients.prompt_client import PromptClient

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

        super(Processor, self).__init__(
            **params | {
                "input_queue": input_queue,
                "output_queue": output_queue,
                "subscriber": subscriber,
                "input_schema": AgentRequest,
                "output_schema": AgentResponse,
                "prompt_request_queue": prompt_request_queue,
                "prompt_response_queue": prompt_response_queue,
            }
        )

        self.prompt = PromptClient(
            subscriber=subscriber,
            input_queue=prompt_request_queue,
            output_queue=prompt_response_queue,
            pulsar_host = self.pulsar_host
        )

        # Need to be able to feed requests to myself
        self.recursive_input = self.client.create_producer(
            topic=input_queue,
            schema=JsonSchema(AgentRequest),
        )

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
                history = v.history
            else:
                history = []

            if len(history) == 0:

                print("Send response...", flush=True)

                thought = "Maybe, just maybe..."

                r = AgentResponse(
                    answer=None,
                    error=None,
                    thought=thought,
                    observation=None,
                )

                self.producer.send(r, properties={"id": id})

                r = AgentResponse(
                    answer=None,
                    error=None,
                    thought=None,
                    observation="I have imagined myself",
                )

                self.producer.send(r, properties={"id": id})

                r = AgentRequest(
                    question=v.question,
                    plan=v.plan,
                    state=v.state,
                    history=[
                        AgentStep(
                            thought=thought,
                            action="asd",
                            arguments={
                                "asd": "def",
                                "ghi": "alskd",
                            },
                            observation="hello world",
                        )
                    ]
                )

                self.recursive_input.send(r, properties={"id": id})

                print("Done.", flush=True)

                return

            else:

                print("Send response...", flush=True)

                r = AgentResponse(
                    answer="Here is the answer",
                    error=None,
                    thought=None,
                )

                self.producer.send(r, properties={"id": id})

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

def run():

    Processor.start(module, __doc__)

