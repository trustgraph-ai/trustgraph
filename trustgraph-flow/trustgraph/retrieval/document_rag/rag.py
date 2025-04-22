
"""
Simple RAG service, performs query using document RAG an LLM.
Input is query, output is response.
"""

from ... schema import DocumentRagQuery, DocumentRagResponse, Error
from . document_rag import DocumentRag
from ... base import FlowProcessor, ConsumerSpec, ProducerSpec
from ... base import PromptClientSpec, EmbeddingsClientSpec
from ... base import DocumentEmbeddingsClientSpec

default_ident = "document-rag"

class Processor(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id", default_ident)

        doc_limit = params.get("doc_limit", 5)

        super(Processor, self).__init__(
            **params | {
                "id": id,
                "doc_limit": doc_limit,
            }
        )

        self.doc_limit = doc_limit

        self.register_specification(
            ConsumerSpec(
                name = "request",
                schema = DocumentRagQuery,
                handler = self.on_request,
            )
        )

        self.register_specification(
            EmbeddingsClientSpec(
                request_name = "embeddings-request",
                response_name = "embeddings-response",
            )
        )

        self.register_specification(
            DocumentEmbeddingsClientSpec(
                request_name = "document-embeddings-request",
                response_name = "document-embeddings-response",
            )
        )

        self.register_specification(
            PromptClientSpec(
                request_name = "prompt-request",
                response_name = "prompt-response",
            )
        )

        self.register_specification(
            ProducerSpec(
                name = "response",
                schema = DocumentRagResponse,
            )
        )

    async def on_request(self, msg, consumer, flow):

        try:

            self.rag = DocumentRag(
                embeddings_client = flow("embeddings-request"),
                doc_embeddings_client = flow("document-embeddings-request"),
                prompt_client = flow("prompt-request"),
                verbose=True,
            )

            v = msg.value()

            # Sender-produced ID
            id = msg.properties()["id"]

            print(f"Handling input {id}...", flush=True)

            if v.doc_limit:
                doc_limit = v.doc_limit
            else:
                doc_limit = self.doc_limit

            response = await self.rag.query(v.query, doc_limit=doc_limit)

            await flow("response").send(
                DocumentRagResponse(
                    response = response,
                    error = None
                ),
                properties = {"id": id}
            )

            print("Done.", flush=True)

        except Exception as e:

            print(f"Exception: {e}")

            print("Send error response...", flush=True)

            await flow("response").send(
                DocumentRagResponse(
                    response = None,
                    error = Error(
                        type = "document-rag-error",
                        message = str(e),
                    ),
                ),
                properties = {"id": id}
            )

    @staticmethod
    def add_args(parser):

        FlowProcessor.add_args(parser)

        parser.add_argument(
            '-d', '--doc-limit',
            type=int,
            default=20,
            help=f'Default document fetch limit (default: 10)'
        )

def run():

    Processor.launch(default_ident, __doc__)

