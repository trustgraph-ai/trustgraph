
"""
Document embeddings, calls the embeddings service to get embeddings for a
chunk of text.  Input is chunk of text plus metadata.
Output is chunk plus embedding.
"""

from ... schema import Chunk, ChunkEmbeddings, DocumentEmbeddings
from ... schema import EmbeddingsRequest, EmbeddingsResponse

from ... base import FlowProcessor, RequestResponseSpec, ConsumerSpec
from ... base import ProducerSpec

import logging

logger = logging.getLogger(__name__)

default_ident = "document-embeddings"

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
                schema = Chunk,
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
                schema = DocumentEmbeddings
            )
        )

    async def on_message(self, msg, consumer, flow):

        v = msg.value()
        logger.info(f"Indexing {v.metadata.id}...")

        try:

            resp = await flow("embeddings-request").request(
                EmbeddingsRequest(
                    text = v.chunk
                )
            )

            vectors = resp.vectors

            embeds = [
                ChunkEmbeddings(
                    chunk=v.chunk,
                    vectors=vectors,
                )
            ]

            r = DocumentEmbeddings(
                metadata=v.metadata,
                chunks=embeds,
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

