"""
Triples query service.  Input is a (s, p, o) triple, some values may be
null.  Output is a list of triples.
"""

from __future__ import annotations

from argparse import ArgumentParser

import logging

from .. schema import TriplesQueryRequest, TriplesQueryResponse, Error
from .. schema import Term, Triple

from . flow_processor import FlowProcessor
from . consumer_spec import  ConsumerSpec
from . producer_spec import ProducerSpec

# Module logger
logger = logging.getLogger(__name__)

default_ident = "triples-query"
default_concurrency = 10

class TriplesQueryService(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id")
        concurrency = params.get("concurrency", default_concurrency)

        super(TriplesQueryService, self).__init__(**params | { "id": id })

        self.register_specification(
            ConsumerSpec(
                name = "request",
                schema = TriplesQueryRequest,
                handler = self.on_message,
                concurrency = concurrency,
            )
        )

        self.register_specification(
            ProducerSpec(
                name = "response",
                schema = TriplesQueryResponse,
            )
        )

    async def on_message(self, msg, consumer, flow):

        try:

            request = msg.value()

            # Sender-produced ID
            id = msg.properties()["id"]

            logger.debug(f"Handling triples query request {id}...")

            if request.streaming:
                # Streaming mode: send batches
                async for batch, is_final in self.query_triples_stream(request):
                    r = TriplesQueryResponse(
                        triples=batch,
                        error=None,
                        is_final=is_final,
                    )
                    await flow("response").send(r, properties={"id": id})
                logger.debug("Triples query streaming completed")
            else:
                # Non-streaming mode: single response
                triples = await self.query_triples(request)
                logger.debug("Sending triples query response...")
                r = TriplesQueryResponse(triples=triples, error=None)
                await flow("response").send(r, properties={"id": id})
                logger.debug("Triples query request completed")

        except Exception as e:

            logger.error(f"Exception in triples query service: {e}", exc_info=True)

            logger.info("Sending error response...")

            r = TriplesQueryResponse(
                error = Error(
                    type = "triples-query-error",
                    message = str(e),
                ),
                triples = None,
            )

            await flow("response").send(r, properties={"id": id})

    async def query_triples_stream(self, request):
        """
        Streaming query - yields (batch, is_final) tuples.
        Default implementation batches results from query_triples.
        Override for true streaming from backend.
        """
        triples = await self.query_triples(request)
        batch_size = request.batch_size if request.batch_size > 0 else 20

        for i in range(0, len(triples), batch_size):
            batch = triples[i:i + batch_size]
            is_final = (i + batch_size >= len(triples))
            yield batch, is_final

        # Handle empty result
        if len(triples) == 0:
            yield [], True

    @staticmethod
    def add_args(parser: ArgumentParser) -> None:

        FlowProcessor.add_args(parser)

        parser.add_argument(
            '-c', '--concurrency',
            type=int,
            default=default_concurrency,
            help=f'Number of concurrent requests (default: {default_concurrency})'
        )

def run() -> None:

    Processor.launch(default_ident, __doc__)

