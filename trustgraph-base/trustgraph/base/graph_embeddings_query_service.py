
"""
Graph embeddings query service.  Input is vectors.  Output is list of
embeddings.
"""

import logging

from .. schema import GraphEmbeddingsRequest, GraphEmbeddingsResponse
from .. schema import Error, Term

from . flow_processor import FlowProcessor
from . consumer_spec import ConsumerSpec
from . producer_spec import ProducerSpec

# Module logger
logger = logging.getLogger(__name__)

default_ident = "ge-query"

class GraphEmbeddingsQueryService(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id")

        super(GraphEmbeddingsQueryService, self).__init__(
            **params | { "id": id }
        )

        self.register_specification(
            ConsumerSpec(
                name = "request",
                schema = GraphEmbeddingsRequest,
                handler = self.on_message
            )
        )

        self.register_specification(
            ProducerSpec(
                name = "response",
                schema = GraphEmbeddingsResponse,
            )
        )

    async def on_message(self, msg, consumer, flow):

        try:

            request = msg.value()

            # Sender-produced ID
            id = msg.properties()["id"]

            logger.debug(f"Handling graph embeddings query request {id}...")

            entities = await self.query_graph_embeddings(request)

            logger.debug("Sending graph embeddings query response...")
            r = GraphEmbeddingsResponse(entities=entities, error=None)
            await flow("response").send(r, properties={"id": id})

            logger.debug("Graph embeddings query request completed")

        except Exception as e:

            logger.error(f"Exception in graph embeddings query service: {e}", exc_info=True)

            logger.info("Sending error response...")

            r = GraphEmbeddingsResponse(
                error=Error(
                    type = "graph-embeddings-query-error",
                    message = str(e),
                ),
                response=None,
            )

            await flow("response").send(r, properties={"id": id})

    @staticmethod
    def add_args(parser):

        FlowProcessor.add_args(parser)

def run():

    Processor.launch(default_ident, __doc__)

