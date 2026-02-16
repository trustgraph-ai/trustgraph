
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
default_batch_size = 5

class Processor(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id")
        self.batch_size = params.get("batch_size", default_batch_size)

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

            # Send in batches to avoid oversized messages
            for i in range(0, len(entities), self.batch_size):
                batch = entities[i:i + self.batch_size]
                r = GraphEmbeddings(
                    metadata=v.metadata,
                    entities=batch,
                )
                await flow("output").send(r)

        except Exception as e:
            logger.error("Exception occurred", exc_info=True)

            # Retry
            raise e

        logger.info("Done.")

    @staticmethod
    def add_args(parser):

        parser.add_argument(
            '--batch-size',
            type=int,
            default=default_batch_size,
            help=f'Maximum entities per output message (default: {default_batch_size})'
        )

        FlowProcessor.add_args(parser)

def run():

    Processor.launch(default_ident, __doc__)

