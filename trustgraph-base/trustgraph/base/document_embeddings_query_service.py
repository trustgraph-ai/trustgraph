
"""
Document embeddings query service.  Input is vectors.  Output is list of
embeddings.
"""

import logging

from .. schema import DocumentEmbeddingsRequest, DocumentEmbeddingsResponse
from .. schema import Error, Value

from . flow_processor import FlowProcessor
from . consumer_spec import ConsumerSpec
from . producer_spec import ProducerSpec

# Module logger
logger = logging.getLogger(__name__)

default_ident = "ge-query"

class DocumentEmbeddingsQueryService(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id")

        super(DocumentEmbeddingsQueryService, self).__init__(
            **params | { "id": id }
        )

        self.register_specification(
            ConsumerSpec(
                name = "request",
                schema = DocumentEmbeddingsRequest,
                handler = self.on_message
            )
        )

        self.register_specification(
            ProducerSpec(
                name = "response",
                schema = DocumentEmbeddingsResponse,
            )
        )

    async def on_message(self, msg, consumer, flow):

        try:

            request = msg.value()

            # Sender-produced ID
            id = msg.properties()["id"]

            logger.debug(f"Handling document embeddings query request {id}...")

            docs = await self.query_document_embeddings(request)

            logger.debug("Sending document embeddings query response...")
            r = DocumentEmbeddingsResponse(chunks=docs, error=None)
            await flow("response").send(r, properties={"id": id})

            logger.debug("Document embeddings query request completed")

        except Exception as e:

            logger.error(f"Exception in document embeddings query service: {e}", exc_info=True)

            logger.info("Sending error response...")

            r = DocumentEmbeddingsResponse(
                error=Error(
                    type = "document-embeddings-query-error",
                    message = str(e),
                ),
                chunks=None,
            )

            await flow("response").send(r, properties={"id": id})

    @staticmethod
    def add_args(parser):

        FlowProcessor.add_args(parser)

def run():

    Processor.launch(default_ident, __doc__)

