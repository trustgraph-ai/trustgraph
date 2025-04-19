
"""
Embeddings resolution base class
"""

import time
from prometheus_client import Histogram

from .. schema import EmbeddingsRequest, EmbeddingsResponse, Error
from .. exceptions import TooManyRequests
from .. base import FlowProcessor, ConsumerSpec, ProducerSpec

default_ident = "embeddings"

class EmbeddingsService(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id")

        super(EmbeddingsService, self).__init__(**params | { "id": id })

        self.register_specification(
            ConsumerSpec(
                name = "request",
                schema = EmbeddingsRequest,
                handler = self.on_request
            )
        )

        self.register_specification(
            ProducerSpec(
                name = "response",
                schema = EmbeddingsResponse
            )
        )

    async def on_request(self, msg, consumer, flow):

        try:

            request = msg.value()

            # Sender-produced ID

            id = msg.properties()["id"]

            print("Handling request", id, "...", flush=True)

            vectors = await self.on_embeddings(request.text)

            await flow("response").send(
                EmbeddingsResponse(
                    error = None,
                    vectors = vectors,
                ),
                properties={"id": id}
            )

            print("Handled.", flush=True)

        except TooManyRequests as e:
            raise e

        except Exception as e:

            # Apart from rate limits, treat all exceptions as unrecoverable

            print(f"Exception: {e}", flush=True)

            print("Send error response...", flush=True)

            await flow.producer["response"].send(
                EmbeddingsResponse(
                    error=Error(
                        type = "embeddings-error",
                        message = str(e),
                    ),
                    vectors=None,
                ),
                properties={"id": id}
            )

    @staticmethod
    def add_args(parser):

        FlowProcessor.add_args(parser)



