
"""
Graph embeddings query service.  Input is vectors.  Output is list of
embeddings.
"""

from .... schema import GraphEmbeddingsRequest, GraphEmbeddingsResponse
from .... schema import Error, Value

from .... base import FlowProcessor, GraphEmbeddingsQueryService, ConsumerSpec
from .... base import ProducerSpec

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

            print(f"Handling input {id}...", flush=True)

            entities = self.query_graph_embeddings(request)

            print("Send response...", flush=True)
            r = GraphEmbeddingsResponse(entities=entities, error=None)
            await flow("response").send(r, properties={"id": id})

            print("Done.", flush=True)

        except Exception as e:

            print(f"Exception: {e}")

            print("Send error response...", flush=True)

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

        GraphEmbeddingsQueryService.add_args(parser)

def run():

    Processor.launch(default_ident, __doc__)

