
"""
Document embeddings store base class
"""

from .. schema import DocumentEmbeddings
from .. base import FlowProcessor, ConsumerSpec
from .. exceptions import TooManyRequests

default_ident = "document-embeddings-write"

class DocumentEmbeddingsStoreService(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id")

        super(DocumentEmbeddingsStoreService, self).__init__(
            **params | { "id": id }
        )

        self.register_specification(
            ConsumerSpec(
                name = "input",
                schema = DocumentEmbeddings,
                handler = self.on_message
            )
        )

    async def on_message(self, msg, consumer, flow):

        try:

            request = msg.value()

            await self.store_document_embeddings(request)

        except TooManyRequests as e:
            raise e

        except Exception as e:
            
            print(f"Exception: {e}")
            raise e

    @staticmethod
    def add_args(parser):

        FlowProcessor.add_args(parser)

