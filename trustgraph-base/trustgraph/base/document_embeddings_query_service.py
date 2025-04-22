
"""
Document embeddings query service.  Input is vectors.  Output is list of
embeddings.
"""

from .. schema import DocumentEmbeddingsRequest, DocumentEmbeddingsResponse
from .. schema import Error, Value

from . flow_processor import FlowProcessor
from . consumer_spec import ConsumerSpec
from . producer_spec import ProducerSpec

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

            print(f"Handling input {id}...", flush=True)

            docs = await self.query_document_embeddings(request)

            print("Send response...", flush=True)
            r = DocumentEmbeddingsResponse(documents=docs, error=None)
            await flow("response").send(r, properties={"id": id})

            print("Done.", flush=True)

        except Exception as e:

            print(f"Exception: {e}")

            print("Send error response...", flush=True)

            r = DocumentEmbeddingsResponse(
                error=Error(
                    type = "document-embeddings-query-error",
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

