
"""
Simple RAG service, performs query using document RAG an LLM.
Input is query, output is response.
"""

import logging

from ... schema import DocumentRagQuery, DocumentRagResponse, Error
from ... schema import Triples, Metadata
from ... provenance import GRAPH_RETRIEVAL
from . document_rag import DocumentRag
from ... base import FlowProcessor, ConsumerSpec, ProducerSpec
from ... base import PromptClientSpec, EmbeddingsClientSpec
from ... base import DocumentEmbeddingsClientSpec
from ... base import RerankerClientSpec
from ... base import LibrarianSpec

# Module logger
logger = logging.getLogger(__name__)

default_ident = "document-rag"

class Processor(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id", default_ident)

        doc_limit = params.get("doc_limit", 5)

        # Instance-default candidate-pool size fetched before cross-encoder
        # reranking; the rerank step narrows it back down to doc_limit for the
        # LLM. 0 means the core derives it (OVERFETCH_FACTOR x doc_limit).
        fetch_limit = params.get("fetch_limit", 0)
        rerank_diversity_mode = params.get("rerank_diversity_mode", "none")
        rerank_diversity_lambda = params.get("rerank_diversity_lambda", 0.7)
        fetch_chunk_timeout = params.get("fetch_chunk_timeout", 120)

        super(Processor, self).__init__(
            **params | {
                "id": id,
                "doc_limit": doc_limit,
                "fetch_limit": fetch_limit,
                "rerank_diversity_mode": rerank_diversity_mode,
                "rerank_diversity_lambda": rerank_diversity_lambda,
                "fetch_chunk_timeout": fetch_chunk_timeout,
            }
        )

        self.doc_limit = doc_limit
        self.fetch_limit = fetch_limit
        self.rerank_diversity_mode = rerank_diversity_mode
        self.rerank_diversity_lambda = rerank_diversity_lambda
        self.fetch_chunk_timeout = fetch_chunk_timeout

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
            RerankerClientSpec(
                request_name = "reranker-request",
                response_name = "reranker-response",
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

        self.register_specification(
            LibrarianSpec()
        )

    async def on_request(self, msg, consumer, flow):

        try:

            v = msg.value()

            # Sender-produced ID
            id = msg.properties()["id"]

            logger.info(f"Handling input {id}...")

            async def fetch_chunk(chunk_id, timeout=self.fetch_chunk_timeout):
                return await flow.librarian.fetch_document_text(
                    document_id=chunk_id, timeout=timeout,
                )

            self.rag = DocumentRag(
                embeddings_client = flow("embeddings-request"),
                doc_embeddings_client = flow("document-embeddings-request"),
                prompt_client = flow("prompt-request"),
                fetch_chunk = fetch_chunk,
                reranker_client = flow("reranker-request"),
                verbose=True,
                rerank_diversity_mode=self.rerank_diversity_mode,
                rerank_diversity_lambda=self.rerank_diversity_lambda,
            )

            if v.doc_limit:
                doc_limit = v.doc_limit
            else:
                doc_limit = self.doc_limit

            # Candidate-pool size: per-request override, else the instance
            # default; 0 lets the core derive it from doc_limit.
            if v.fetch_limit:
                fetch_limit = v.fetch_limit
            else:
                fetch_limit = self.fetch_limit

            async def send_explainability(triples, explain_id):
                await flow("explainability").send(Triples(
                    metadata=Metadata(
                        id=explain_id,
                        collection=v.collection,
                    ),
                    triples=triples,
                ))

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

            async def save_answer(doc_id, answer_text):
                await flow.librarian.save_document(
                    doc_id=doc_id,
                    content=answer_text,
                    title=f"DocumentRAG Answer: {v.query[:50]}...",
                    document_type="answer",
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
                    fetch_limit=fetch_limit,
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
                    fetch_limit=fetch_limit,
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

        parser.add_argument(
            '--fetch-limit',
            type=int,
            default=0,
            help='Candidate chunks to fetch from the vector store and rerank '
                 'before keeping the top doc-limit for the LLM '
                 '(default: derive from doc-limit)'
        )

        parser.add_argument(
            '--rerank-diversity-mode',
            choices=['none', 'mmr'],
            default='none',
            help='Optional diversity-aware selection after reranking (default: none)'
        )

        parser.add_argument(
            '--rerank-diversity-lambda',
            type=float,
            default=0.7,
            help='MMR relevance/diversity tradeoff, higher values prefer relevance'
        )

        parser.add_argument(
            '--fetch-chunk-timeout',
            type=int,
            default=120,
            help='Timeout in seconds for fetching a document chunk from the '
                 'librarian (default: 120)'
        )

def run():

    Processor.launch(default_ident, __doc__)
