
"""
Simple RAG service, performs query using document RAG an LLM.
Input is query, output is response.
"""

import asyncio
import base64
import logging

import uuid

from ... schema import DocumentRagQuery, DocumentRagResponse, Error
from ... schema import LibrarianRequest, LibrarianResponse, DocumentMetadata
from ... schema import Triples, Metadata
from ... provenance import GRAPH_RETRIEVAL
from . document_rag import DocumentRag
from ... base import FlowProcessor, ConsumerSpec, ProducerSpec
from ... base import PromptClientSpec, EmbeddingsClientSpec
from ... base import DocumentEmbeddingsClientSpec
from ... base import LibrarianClient

# Module logger
logger = logging.getLogger(__name__)

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

        self.register_specification(
            ProducerSpec(
                name = "explainability",
                schema = Triples,
            )
        )

        # Librarian client
        self.librarian = LibrarianClient(
            id=id,
            backend=self.pubsub,
            taskgroup=self.taskgroup,
        )

    async def start(self):
        await super(Processor, self).start()
        await self.librarian.start()

    async def fetch_chunk_content(self, chunk_id, workspace, timeout=120):
        """Fetch chunk content from librarian. Chunks are small so
        single request-response is fine."""
        return await self.librarian.fetch_document_text(
            document_id=chunk_id, workspace=workspace, timeout=timeout,
        )

    async def save_answer_content(self, doc_id, workspace, content, title=None, timeout=120):
        """Save answer content to the librarian."""

        doc_metadata = DocumentMetadata(
            id=doc_id,
            workspace=workspace,
            kind="text/plain",
            title=title or "DocumentRAG Answer",
            document_type="answer",
        )

        request = LibrarianRequest(
            operation="add-document",
            document_id=doc_id,
            document_metadata=doc_metadata,
            content=base64.b64encode(content.encode("utf-8")).decode("utf-8"),
            workspace=workspace,
        )

        await self.librarian.request(request, timeout=timeout)
        return doc_id

    async def on_request(self, msg, consumer, flow):

        try:

            self.rag = DocumentRag(
                embeddings_client = flow("embeddings-request"),
                doc_embeddings_client = flow("document-embeddings-request"),
                prompt_client = flow("prompt-request"),
                fetch_chunk = self.fetch_chunk_content,
                verbose=True,
            )

            v = msg.value()

            # Sender-produced ID
            id = msg.properties()["id"]

            logger.info(f"Handling input {id}...")

            if v.doc_limit:
                doc_limit = v.doc_limit
            else:
                doc_limit = self.doc_limit

            # Real-time explainability callback - emits triples and IDs as they're generated
            # Triples are stored in the request's collection with a named graph (urn:graph:retrieval)
            async def send_explainability(triples, explain_id):
                # Send triples to explainability queue - stores in same collection with named graph
                await flow("explainability").send(Triples(
                    metadata=Metadata(
                        id=explain_id,
                        collection=v.collection,
                    ),
                    triples=triples,
                ))

                # Send explain data to response queue
                await flow("response").send(
                    DocumentRagResponse(
                        response=None,
                        explain_id=explain_id,
                        explain_graph=GRAPH_RETRIEVAL,
                        explain_triples=triples,
                        message_type="explain",
                    ),
                    properties={"id": id}
                )

            # Callback to save answer content to librarian
            async def save_answer(doc_id, answer_text):
                await self.save_answer_content(
                    doc_id=doc_id,
                    workspace=flow.workspace,
                    content=answer_text,
                    title=f"DocumentRAG Answer: {v.query[:50]}...",
                )

            # Check if streaming is requested
            if v.streaming:
                # Define async callback for streaming chunks
                # Receives chunk text and end_of_stream flag from prompt client
                async def send_chunk(chunk, end_of_stream):
                    await flow("response").send(
                        DocumentRagResponse(
                            response=chunk,
                            end_of_stream=end_of_stream,
                            message_type="chunk",
                            error=None
                        ),
                        properties={"id": id}
                    )

                # Query with streaming enabled
                # All chunks (including final one with end_of_stream=True) are sent via callback
                response, usage = await self.rag.query(
                    v.query,
                    workspace=flow.workspace,
                    collection=v.collection,
                    doc_limit=doc_limit,
                    streaming=True,
                    chunk_callback=send_chunk,
                    explain_callback=send_explainability,
                    save_answer_callback=save_answer,
                )

                # Send end_of_session to signal entire session is complete
                await flow("response").send(
                    DocumentRagResponse(
                        response=None,
                        end_of_session=True,
                        message_type="end",
                        in_token=usage.get("in_token"),
                        out_token=usage.get("out_token"),
                        model=usage.get("model"),
                    ),
                    properties={"id": id}
                )
            else:
                # Non-streaming path - single response with answer and token usage
                response, usage = await self.rag.query(
                    v.query,
                    workspace=flow.workspace,
                    collection=v.collection,
                    doc_limit=doc_limit,
                    explain_callback=send_explainability,
                    save_answer_callback=save_answer,
                )

                await flow("response").send(
                    DocumentRagResponse(
                        response=response,
                        end_of_stream=True,
                        end_of_session=True,
                        error=None,
                        in_token=usage.get("in_token"),
                        out_token=usage.get("out_token"),
                        model=usage.get("model"),
                    ),
                    properties={"id": id}
                )

            logger.info("Request processing complete")

        except Exception as e:

            logger.error(f"Document RAG service exception: {e}", exc_info=True)

            logger.debug("Sending error response...")

            # Send error response with end_of_stream flag if streaming was requested
            error_response = DocumentRagResponse(
                response = None,
                error = Error(
                    type = "document-rag-error",
                    message = str(e),
                ),
            )

            # If streaming was requested, indicate stream end
            if v.streaming:
                error_response.end_of_stream = True

            await flow("response").send(
                error_response,
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
