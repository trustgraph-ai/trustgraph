
"""
Agent manager service completion base class
"""

import time
from prometheus_client import Histogram

from .. schema import AgentRequest, AgentResponse, Error
from .. exceptions import TooManyRequests
from .. base import FlowProcessor, ConsumerSpec, ProducerSpec

default_ident = "agent-manager"

class AgentService(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id")

        super(AgentService, self).__init__(**params | { "id": id })

        self.register_specification(
            ConsumerSpec(
                name = "request",
                schema = AgentRequest,
                handler = self.on_request
            )
        )

        self.register_specification(
            ProducerSpec(
                name = "next",
                schema = AgentRequest
            )
        )

        self.register_specification(
            ProducerSpec(
                name = "response",
                schema = AgentResponse
            )
        )

    async def on_request(self, msg, consumer, flow):

        try:

            request = msg.value()

            # Sender-produced ID
            id = msg.properties()["id"]

            async def respond(resp):

                await flow("response").send(
                    resp,
                    properties={"id": id}
                )

            async def next(resp):

                await flow("next").send(
                    resp,
                    properties={"id": id}
                )

            await self.agent_request(
                request = request, respond = respond, next = next,
                flow = flow
            )

        except TooManyRequests as e:
            raise e

        except Exception as e:

            # Apart from rate limits, treat all exceptions as unrecoverable
            print(f"on_request Exception: {e}")

            print("Send error response...", flush=True)

            await flow.producer["response"].send(
                AgentResponse(
                    error=Error(
                        type = "agent-error",
                        message = str(e),
                    ),
                    thought = None,
                    observation = None,
                    answer = None,
                ),
                properties={"id": id}
            )

    @staticmethod
    def add_args(parser):

        FlowProcessor.add_args(parser)

