
"""
Graph embeddings store base class
"""

from .. schema import GraphEmbeddings
from .. base import FlowProcessor, ConsumerSpec

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
            
            print(f"Exception: {e}")
            raise e

    @staticmethod
    def add_args(parser):

        FlowProcessor.add_args(parser)

