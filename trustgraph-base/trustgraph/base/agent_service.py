
"""
Agent manager service completion base class
"""

import time
import logging
from prometheus_client import Histogram

from .. schema import AgentRequest, AgentResponse, Error
from .. exceptions import TooManyRequests
from .. base import FlowProcessor, ConsumerSpec, ProducerSpec

# Module logger
logger = logging.getLogger(__name__)

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

        # Get ID early so error handler can use it
        id = msg.properties().get("id", "unknown")

        try:

            request = msg.value()

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
            logger.error(f"Exception in agent service on_request: {e}", exc_info=True)

            logger.info("Sending error response...")

            await flow.producer["response"].send(
                AgentResponse(
                    error=Error(
                        type = "agent-error",
                        message = str(e),
                    ),
                    thought = None,
                    observation = None,
                    answer = None,
                    end_of_message = True,
                    end_of_dialog = True,
                ),
                properties={"id": id}
            )

    @staticmethod
    def add_args(parser):

        FlowProcessor.add_args(parser)

