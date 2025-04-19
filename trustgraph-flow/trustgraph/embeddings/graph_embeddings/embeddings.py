
"""
Graph embeddings, calls the embeddings service to get embeddings for a
set of entity contexts.  Input is entity plus textual context.
Output is entity plus embedding.
"""

from ... schema import EntityContexts, EntityEmbeddings, GraphEmbeddings
from ... schema import EmbeddingsRequest, EmbeddingsResponse

from ... base import FlowProcessor, RequestResponseSpec, ConsumerSpec
from ... base import ProducerSpec

default_ident = "graph-embeddings"

class Processor(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id")

        super(Processor, self).__init__(
            **params | {
                "id": id,
            }
        )

        self.register_specification(
            ConsumerSpec(
                name = "input",
                schema = EntityContexts,
                handler = self.on_message,
            )
        )

        self.register_specification(
            RequestResponseSpec(
                request_name = "embeddings-request",
                request_schema = EmbeddingsRequest,
                response_name = "embeddings-response",
                response_schema = EmbeddingsResponse,
            )
        )

        self.register_specification(
            ProducerSpec(
                name = "output",
                schema = GraphEmbeddings
            )
        )

    async def on_message(self, msg, consumer, flow):

        v = msg.value()
        print(f"Indexing {v.metadata.id}...", flush=True)

        entities = []

        try:

            for entity in v.entities:

                resp = await flow("embeddings-request").request(
                    EmbeddingsRequest(
                        text = entity.context
                    )
                )

                vectors = resp.vectors

                entities.append(
                    EntityEmbeddings(
                        entity=entity.entity,
                        vectors=vectors
                    )
                )

            r = GraphEmbeddings(
                metadata=v.metadata,
                entities=entities,
            )

            await flow("output").send(r)

        except Exception as e:
            print("Exception:", e, flush=True)

            # Retry
            raise e

        print("Done.", flush=True)

    @staticmethod
    def add_args(parser):

        FlowProcessor.add_args(parser)

def run():

    Processor.launch(default_ident, __doc__)

