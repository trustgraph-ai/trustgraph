
"""
Graph embeddings, calls the embeddings service to get embeddings for a
set of entity contexts.  Input is entity plus textual context.
Output is entity plus embedding.
"""

from ... schema import EntityContexts, EntityEmbeddings, GraphEmbeddings
from ... schema import EmbeddingsRequest, EmbeddingsResponse

from ... base import FlowProcessor, EmbeddingsClientSpec, ConsumerSpec
from ... base import ProducerSpec

import logging

logger = logging.getLogger(__name__)

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
            EmbeddingsClientSpec(
                request_name = "embeddings-request",
                response_name = "embeddings-response",
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
        logger.info(f"Indexing {v.metadata.id}...")

        entities = []

        try:

            for entity in v.entities:

                vectors = await flow("embeddings-request").embed(
                    text = entity.context
                )

                entities.append(
                    EntityEmbeddings(
                        entity=entity.entity,
                        vectors=vectors
                    )
                )

            if entities:
                r = GraphEmbeddings(
                    metadata=v.metadata,
                    entities=entities,
                )

                await flow("output").send(r)

        except Exception as e:
            logger.error("Exception occurred", exc_info=True)

            # Retry
            raise e

        logger.info("Done.")

    @staticmethod
    def add_args(parser):

        FlowProcessor.add_args(parser)

def run():

    Processor.launch(default_ident, __doc__)

