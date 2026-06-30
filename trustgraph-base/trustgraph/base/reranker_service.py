
from __future__ import annotations

from argparse import ArgumentParser

import logging

from .. schema import (
    RerankerRequest, RerankerResponse, RerankerResult, Error,
)
from .. exceptions import TooManyRequests
from .. base import FlowProcessor, ConsumerSpec, ProducerSpec, ParameterSpec

logger = logging.getLogger(__name__)

default_ident = "reranker"
default_concurrency = 1

class RerankerService(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id")
        concurrency = params.get("concurrency", 1)

        super(RerankerService, self).__init__(**params | {
            "id": id,
            "concurrency": concurrency,
        })

        self.register_specification(
            ConsumerSpec(
                name = "request",
                schema = RerankerRequest,
                handler = self.on_request,
                concurrency = concurrency,
            )
        )

        self.register_specification(
            ProducerSpec(
                name = "response",
                schema = RerankerResponse
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

            id = msg.properties()["id"]

            logger.debug(f"Handling reranker request {id}...")

            model = flow("model")
            results = await self.on_rerank(
                request.queries, request.documents,
                request.limit, model=model,
            )

            await flow("response").send(
                RerankerResponse(
                    error = None,
                    results = results,
                ),
                properties={"id": id}
            )

            logger.debug("Reranker request handled successfully")

        except TooManyRequests as e:
            raise e

        except Exception as e:

            logger.error(f"Exception in reranker service: {e}", exc_info=True)

            logger.info("Sending error response...")

            await flow.producer["response"].send(
                RerankerResponse(
                    error=Error(
                        type = "reranker-error",
                        message = str(e),
                    ),
                    results=[],
                ),
                properties={"id": id}
            )

    @staticmethod
    def add_args(parser: ArgumentParser) -> None:

        parser.add_argument(
            '-c', '--concurrency',
            type=int,
            default=default_concurrency,
            help=f'Concurrent processing threads (default: {default_concurrency})'
        )

        FlowProcessor.add_args(parser)
