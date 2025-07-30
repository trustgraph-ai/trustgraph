
"""
Graph embeddings store base class
"""

import logging

from .. schema import GraphEmbeddings
from .. base import FlowProcessor, ConsumerSpec
from .. exceptions import TooManyRequests

# Module logger
logger = logging.getLogger(__name__)

default_ident = "graph-embeddings-write"

class GraphEmbeddingsStoreService(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id")

        super(GraphEmbeddingsStoreService, self).__init__(
            **params | { "id": id }
        )

        self.register_specification(
            ConsumerSpec(
                name = "input",
                schema = GraphEmbeddings,
                handler = self.on_message
            )
        )

    async def on_message(self, msg, consumer, flow):

        try:

            request = msg.value()

            await self.store_graph_embeddings(request)

        except TooManyRequests as e:
            raise e

        except Exception as e:
            
            logger.error(f"Exception in graph embeddings store service: {e}", exc_info=True)
            raise e

    @staticmethod
    def add_args(parser):

        FlowProcessor.add_args(parser)

