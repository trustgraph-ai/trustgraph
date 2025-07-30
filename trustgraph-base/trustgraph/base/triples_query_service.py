
"""
Triples query service.  Input is a (s, p, o) triple, some values may be
null.  Output is a list of triples.
"""

import logging

from .. schema import TriplesQueryRequest, TriplesQueryResponse, Error
from .. schema import Value, Triple

from . flow_processor import FlowProcessor
from . consumer_spec import  ConsumerSpec
from . producer_spec import ProducerSpec

# Module logger
logger = logging.getLogger(__name__)

default_ident = "triples-query"

class TriplesQueryService(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id")

        super(TriplesQueryService, self).__init__(**params | { "id": id })

        self.register_specification(
            ConsumerSpec(
                name = "request",
                schema = TriplesQueryRequest,
                handler = self.on_message
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

    @staticmethod
    def add_args(parser):

        FlowProcessor.add_args(parser)

def run():

    Processor.launch(default_ident, __doc__)

