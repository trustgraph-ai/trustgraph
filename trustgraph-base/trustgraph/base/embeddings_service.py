
"""
Embeddings resolution base class
"""

import time
import logging
from prometheus_client import Histogram

from .. schema import EmbeddingsRequest, EmbeddingsResponse, Error
from .. exceptions import TooManyRequests
from .. base import FlowProcessor, ConsumerSpec, ProducerSpec, ParameterSpec

# Module logger
logger = logging.getLogger(__name__)

default_ident = "embeddings"
default_concurrency = 1

class EmbeddingsService(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id")
        concurrency = params.get("concurrency", 1)

        super(EmbeddingsService, self).__init__(**params | {
            "id": id,
            "concurrency": concurrency,
        })

        self.register_specification(
            ConsumerSpec(
                name = "request",
                schema = EmbeddingsRequest,
                handler = self.on_request,
                concurrency = concurrency,
            )
        )

        self.register_specification(
            ProducerSpec(
                name = "response",
                schema = EmbeddingsResponse
            )
        )

        self.register_specification(
            ParameterSpec(
                name = "model",
            )
        )

    async def on_request(self, msg, consumer, flow):

        try:

            request = msg.value()

            # Sender-produced ID

            id = msg.properties()["id"]

            logger.debug(f"Handling embeddings request {id}...")

            # Pass model from request if specified (non-empty), otherwise use default
            model = flow("model")
            vectors = await self.on_embeddings(request.text, model=model)

            await flow("response").send(
                EmbeddingsResponse(
                    error = None,
                    vectors = vectors,
                ),
                properties={"id": id}
            )

            logger.debug("Embeddings request handled successfully")

        except TooManyRequests as e:
            raise e

        except Exception as e:

            # Apart from rate limits, treat all exceptions as unrecoverable

            logger.error(f"Exception in embeddings service: {e}", exc_info=True)

            logger.info("Sending error response...")

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

        parser.add_argument(
            '-c', '--concurrency',
            type=int,
            default=default_concurrency,
            help=f'Concurrent processing threads (default: {default_concurrency})'
        )

        FlowProcessor.add_args(parser)



