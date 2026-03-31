
"""
Simple RAG service, performs query using graph RAG an LLM.
Input is query, output is response.
"""

import asyncio
import base64
import logging
import uuid

from ... schema import GraphRagQuery, GraphRagResponse, Error
from ... schema import Triples, Metadata
from ... schema import LibrarianRequest, LibrarianResponse, DocumentMetadata
from ... schema import librarian_request_queue, librarian_response_queue
from ... provenance import GRAPH_RETRIEVAL
from . graph_rag import GraphRag
from ... base import FlowProcessor, ConsumerSpec, ProducerSpec
from ... base import PromptClientSpec, EmbeddingsClientSpec
from ... base import GraphEmbeddingsClientSpec, TriplesClientSpec
from ... base import Consumer, Producer, ConsumerMetrics, ProducerMetrics

# Module logger
logger = logging.getLogger(__name__)

default_ident = "graph-rag"
default_concurrency = 1
default_librarian_request_queue = librarian_request_queue
default_librarian_response_queue = librarian_response_queue

class Processor(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id", default_ident)
        concurrency = params.get("concurrency", 1)

        entity_limit = params.get("entity_limit", 50)
        triple_limit = params.get("triple_limit", 30)
        max_subgraph_size = params.get("max_subgraph_size", 150)
        max_path_length = params.get("max_path_length", 2)
        edge_score_limit = params.get("edge_score_limit", 30)
        edge_limit = params.get("edge_limit", 25)

        super(Processor, self).__init__(
            **params | {
                "id": id,
                "concurrency": concurrency,
                "entity_limit": entity_limit,
                "triple_limit": triple_limit,
                "max_subgraph_size": max_subgraph_size,
                "max_path_length": max_path_length,
                "edge_score_limit": edge_score_limit,
                "edge_limit": edge_limit,
            }
        )

        self.default_entity_limit = entity_limit
        self.default_triple_limit = triple_limit
        self.default_max_subgraph_size = max_subgraph_size
        self.default_max_path_length = max_path_length
        self.default_edge_score_limit = edge_score_limit
        self.default_edge_limit = edge_limit

        # CRITICAL SECURITY: NEVER share data between users or collections
        # Each user/collection combination MUST have isolated data access
        # Caching must NEVER allow information leakage across these boundaries

        self.register_specification(
            ConsumerSpec(
                name = "request",
                schema = GraphRagQuery,
                handler = self.on_request,
                concurrency = concurrency,
            )
        )

        self.register_specification(
            EmbeddingsClientSpec(
                request_name = "embeddings-request",
                response_name = "embeddings-response",
            )
        )

        self.register_specification(
            GraphEmbeddingsClientSpec(
                request_name = "graph-embeddings-request",
                response_name = "graph-embeddings-response",
            )
        )

        self.register_specification(
            TriplesClientSpec(
                request_name = "triples-request",
                response_name = "triples-response",
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
                schema = GraphRagResponse,
            )
        )

        self.register_specification(
            ProducerSpec(
                name = "explainability",
                schema = Triples,
            )
        )

        # Librarian client for storing answer content
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
        self.pending_librarian_requests = {}

        logger.info("Graph RAG service initialized")

    async def start(self):
        await super(Processor, self).start()
        await self.librarian_request_producer.start()
        await self.librarian_response_consumer.start()

    async def on_librarian_response(self, msg, consumer, flow):
        """Handle responses from the librarian service."""
        response = msg.value()
        request_id = msg.properties().get("id")

        if request_id and request_id in self.pending_librarian_requests:
            future = self.pending_librarian_requests.pop(request_id)
            future.set_result(response)

    async def save_answer_content(self, doc_id, user, content, title=None, timeout=120):
        """
        Save answer content to the librarian.

        Args:
            doc_id: ID for the answer document
            user: User ID
            content: Answer text content
            title: Optional title
            timeout: Request timeout in seconds

        Returns:
            The document ID on success
        """
        request_id = str(uuid.uuid4())

        doc_metadata = DocumentMetadata(
            id=doc_id,
            user=user,
            kind="text/plain",
            title=title or "GraphRAG Answer",
            document_type="answer",
        )

        request = LibrarianRequest(
            operation="add-document",
            document_id=doc_id,
            document_metadata=doc_metadata,
            content=base64.b64encode(content.encode("utf-8")).decode("utf-8"),
            user=user,
        )

        # Create future for response
        future = asyncio.get_event_loop().create_future()
        self.pending_librarian_requests[request_id] = future

        try:
            # Send request
            await self.librarian_request_producer.send(
                request, properties={"id": request_id}
            )

            # Wait for response
            response = await asyncio.wait_for(future, timeout=timeout)

            if response.error:
                raise RuntimeError(
                    f"Librarian error saving answer: {response.error.type}: {response.error.message}"
                )

            return doc_id

        except asyncio.TimeoutError:
            self.pending_librarian_requests.pop(request_id, None)
            raise RuntimeError(f"Timeout saving answer document {doc_id}")

    async def on_request(self, msg, consumer, flow):

        try:

            v = msg.value()

            # Sender-produced ID
            id = msg.properties()["id"]

            logger.info(f"Handling input {id}...")

            # Track explainability refs for end_of_session signaling
            explainability_refs_emitted = []

            # Real-time explainability callback - emits triples and IDs as they're generated
            # Triples are stored in the user's collection with a named graph (urn:graph:retrieval)
            async def send_explainability(triples, explain_id):
                # Send triples to explainability queue - stores in same collection with named graph
                await flow("explainability").send(Triples(
                    metadata=Metadata(
                        id=explain_id,
                        user=v.user,
                        collection=v.collection,  # Store in user's collection, not separate explainability collection
                    ),
                    triples=triples,
                ))

                # Send explain ID and graph to response queue
                await flow("response").send(
                    GraphRagResponse(
                        message_type="explain",
                        explain_id=explain_id,
                        explain_graph=GRAPH_RETRIEVAL,
                    ),
                    properties={"id": id}
                )

                explainability_refs_emitted.append(explain_id)

            # CRITICAL SECURITY: Create new GraphRag instance per request
            # This ensures proper isolation between users and collections
            # Flow clients are request-scoped and must not be shared
            rag = GraphRag(
                embeddings_client=flow("embeddings-request"),
                graph_embeddings_client=flow("graph-embeddings-request"),
                triples_client=flow("triples-request"),
                prompt_client=flow("prompt-request"),
                verbose=True,
            )

            if v.entity_limit:
                entity_limit = v.entity_limit
            else:
                entity_limit = self.default_entity_limit

            if v.triple_limit:
                triple_limit = v.triple_limit
            else:
                triple_limit = self.default_triple_limit

            if v.max_subgraph_size:
                max_subgraph_size = v.max_subgraph_size
            else:
                max_subgraph_size = self.default_max_subgraph_size

            if v.max_path_length:
                max_path_length = v.max_path_length
            else:
                max_path_length = self.default_max_path_length

            if v.edge_score_limit:
                edge_score_limit = v.edge_score_limit
            else:
                edge_score_limit = self.default_edge_score_limit

            if v.edge_limit:
                edge_limit = v.edge_limit
            else:
                edge_limit = self.default_edge_limit

            # Callback to save answer content to librarian
            async def save_answer(doc_id, answer_text):
                await self.save_answer_content(
                    doc_id=doc_id,
                    user=v.user,
                    content=answer_text,
                    title=f"GraphRAG Answer: {v.query[:50]}...",
                )

            # Check if streaming is requested
            if v.streaming:
                # Define async callback for streaming chunks
                # Receives chunk text and end_of_stream flag from prompt client
                async def send_chunk(chunk, end_of_stream):
                    await flow("response").send(
                        GraphRagResponse(
                            message_type="chunk",
                            response=chunk,
                            end_of_stream=end_of_stream,
                            error=None
                        ),
                        properties={"id": id}
                    )

                # Query with streaming and real-time explain
                response = await rag.query(
                    query = v.query, user = v.user, collection = v.collection,
                    entity_limit = entity_limit, triple_limit = triple_limit,
                    max_subgraph_size = max_subgraph_size,
                    max_path_length = max_path_length,
                    edge_score_limit = edge_score_limit,
                    edge_limit = edge_limit,
                    streaming = True,
                    chunk_callback = send_chunk,
                    explain_callback = send_explainability,
                    save_answer_callback = save_answer,
                    parent_uri = v.parent_uri,
                )

            else:
                # Non-streaming path with real-time explain
                response = await rag.query(
                    query = v.query, user = v.user, collection = v.collection,
                    entity_limit = entity_limit, triple_limit = triple_limit,
                    max_subgraph_size = max_subgraph_size,
                    max_path_length = max_path_length,
                    edge_score_limit = edge_score_limit,
                    edge_limit = edge_limit,
                    explain_callback = send_explainability,
                    save_answer_callback = save_answer,
                    parent_uri = v.parent_uri,
                )

                # Send chunk with response
                await flow("response").send(
                    GraphRagResponse(
                        message_type="chunk",
                        response=response,
                        end_of_stream=True,
                        error=None,
                    ),
                    properties={"id": id}
                )

            # Send final message to close session
            await flow("response").send(
                GraphRagResponse(
                    message_type="chunk",
                    response="",
                    end_of_session=True,
                ),
                properties={"id": id}
            )

            logger.info("Request processing complete")

        except Exception as e:

            logger.error(f"Graph RAG service exception: {e}", exc_info=True)

            logger.debug("Sending error response...")

            # Send error response and close session
            await flow("response").send(
                GraphRagResponse(
                    message_type="chunk",
                    error=Error(
                        type="graph-rag-error",
                        message=str(e),
                    ),
                    end_of_stream=True,
                    end_of_session=True,
                ),
                properties={"id": id}
            )

    @staticmethod
    def add_args(parser):

        parser.add_argument(
            '-c', '--concurrency',
            type=int,
            default=default_concurrency,
            help=f'Concurrent processing threads (default: {default_concurrency})'
        )

        FlowProcessor.add_args(parser)

        parser.add_argument(
            '-e', '--entity-limit',
            type=int,
            default=50,
            help=f'Default entity vector fetch limit (default: 50)'
        )

        parser.add_argument(
            '-t', '--triple-limit',
            type=int,
            default=30,
            help=f'Default triple query limit, per query (default: 30)'
        )

        parser.add_argument(
            '-u', '--max-subgraph-size',
            type=int,
            default=150,
            help=f'Default max subgraph size (default: 150)'
        )

        parser.add_argument(
            '-a', '--max-path-length',
            type=int,
            default=2,
            help=f'Default max path length (default: 2)'
        )

        parser.add_argument(
            '--edge-score-limit',
            type=int,
            default=30,
            help=f'Semantic pre-filter limit before LLM scoring (default: 30)'
        )

        parser.add_argument(
            '--edge-limit',
            type=int,
            default=25,
            help=f'Max edges after LLM scoring (default: 25)'
        )

        # Note: Explainability triples are now stored in the user's collection
        # with the named graph urn:graph:retrieval (no separate collection needed)

def run():

    Processor.launch(default_ident, __doc__)

