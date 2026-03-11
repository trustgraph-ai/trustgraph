
"""
Simple RAG service, performs query using document RAG an LLM.
Input is query, output is response.
"""

import asyncio
import base64
import logging

from ... schema import DocumentRagQuery, DocumentRagResponse, Error
from ... schema import LibrarianRequest, LibrarianResponse
from ... schema import librarian_request_queue, librarian_response_queue
from ... schema import Triples, Metadata
from ... provenance import GRAPH_RETRIEVAL
from . document_rag import DocumentRag
from ... base import FlowProcessor, ConsumerSpec, ProducerSpec
from ... base import PromptClientSpec, EmbeddingsClientSpec
from ... base import DocumentEmbeddingsClientSpec
from ... base import Consumer, Producer
from ... base import ConsumerMetrics, ProducerMetrics

# Module logger
logger = logging.getLogger(__name__)

default_ident = "document-rag"
default_librarian_request_queue = librarian_request_queue
default_librarian_response_queue = librarian_response_queue

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

        # Librarian client for fetching chunk content from Garage
        librarian_request_q = params.get(
            "librarian_request_queue", default_librarian_request_queue
        )
        librarian_response_q = params.get(
            "librarian_response_queue", default_librarian_response_queue
        )

        librarian_request_metrics = ProducerMetrics(
            processor=id, flow=None, name="librarian-request"
        )

        self.librarian_request_producer = Producer(
            backend=self.pubsub,
            topic=librarian_request_q,
            schema=LibrarianRequest,
            metrics=librarian_request_metrics,
        )

        librarian_response_metrics = ConsumerMetrics(
            processor=id, flow=None, name="librarian-response"
        )

        self.librarian_response_consumer = Consumer(
            taskgroup=self.taskgroup,
            backend=self.pubsub,
            flow=None,
            topic=librarian_response_q,
            subscriber=f"{id}-librarian",
            schema=LibrarianResponse,
            handler=self.on_librarian_response,
            metrics=librarian_response_metrics,
        )

        # Pending librarian requests: request_id -> asyncio.Future
        self.pending_requests = {}

    async def start(self):
        await super(Processor, self).start()
        await self.librarian_request_producer.start()
        await self.librarian_response_consumer.start()

    async def on_librarian_response(self, msg, consumer, flow):
        """Handle responses from the librarian service."""
        response = msg.value()
        request_id = msg.properties().get("id")

        if request_id in self.pending_requests:
            future = self.pending_requests.pop(request_id)
            future.set_result(response)
        else:
            logger.warning(f"Received unexpected librarian response: {request_id}")

    async def fetch_chunk_content(self, chunk_id, user, timeout=120):
        """Fetch chunk content from librarian/Garage."""
        import uuid
        request_id = str(uuid.uuid4())

        request = LibrarianRequest(
            operation="get-document-content",
            document_id=chunk_id,
            user=user,
        )

        # Create future for response
        future = asyncio.get_event_loop().create_future()
        self.pending_requests[request_id] = future

        try:
            # Send request
            await self.librarian_request_producer.send(
                request, properties={"id": request_id}
            )

            # Wait for response
            response = await asyncio.wait_for(future, timeout=timeout)

            if response.error:
                raise RuntimeError(
                    f"Librarian error: {response.error.type}: {response.error.message}"
                )

            # Content is base64 encoded
            content = response.content
            if isinstance(content, str):
                content = content.encode('utf-8')
            return base64.b64decode(content).decode("utf-8")

        except asyncio.TimeoutError:
            self.pending_requests.pop(request_id, None)
            raise RuntimeError(f"Timeout fetching chunk {chunk_id}")

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
            # Triples are stored in the user's collection with a named graph (urn:graph:retrieval)
            async def send_explainability(triples, explain_id):
                # Send triples to explainability queue - stores in same collection with named graph
                await flow("explainability").send(Triples(
                    metadata=Metadata(
                        id=explain_id,
                        user=v.user,
                        collection=v.collection,  # Store in user's collection
                    ),
                    triples=triples,
                ))

                # Send explain ID and graph to response queue
                await flow("response").send(
                    DocumentRagResponse(
                        response=None,
                        explain_id=explain_id,
                        explain_graph=GRAPH_RETRIEVAL,
                    ),
                    properties={"id": id}
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
                            error=None
                        ),
                        properties={"id": id}
                    )

                # Query with streaming enabled
                # All chunks (including final one with end_of_stream=True) are sent via callback
                await self.rag.query(
                    v.query,
                    user=v.user,
                    collection=v.collection,
                    doc_limit=doc_limit,
                    streaming=True,
                    chunk_callback=send_chunk,
                    explain_callback=send_explainability,
                )
            else:
                # Non-streaming path (existing behavior)
                response = await self.rag.query(
                    v.query,
                    user=v.user,
                    collection=v.collection,
                    doc_limit=doc_limit,
                    explain_callback=send_explainability,
                )

                await flow("response").send(
                    DocumentRagResponse(
                        response = response,
                        end_of_stream = True,
                        error = None
                    ),
                    properties = {"id": id}
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

