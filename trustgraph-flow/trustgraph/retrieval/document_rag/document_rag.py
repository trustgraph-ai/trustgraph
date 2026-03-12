
import asyncio
import logging
import uuid
from datetime import datetime

# Provenance imports
from trustgraph.provenance import (
    docrag_question_uri,
    docrag_exploration_uri,
    docrag_synthesis_uri,
    docrag_question_triples,
    docrag_exploration_triples,
    docrag_synthesis_triples,
    set_graph,
    GRAPH_RETRIEVAL,
)

# Module logger
logger = logging.getLogger(__name__)

LABEL="http://www.w3.org/2000/01/rdf-schema#label"

class Query:

    def __init__(
            self, rag, user, collection, verbose,
            doc_limit=20
    ):
        self.rag = rag
        self.user = user
        self.collection = collection
        self.verbose = verbose
        self.doc_limit = doc_limit

    async def get_vector(self, query):

        if self.verbose:
            logger.debug("Computing embeddings...")

        qembeds = await self.rag.embeddings_client.embed([query])

        if self.verbose:
            logger.debug("Embeddings computed")

        # Return the vector set for the first (only) text
        return qembeds[0] if qembeds else []

    async def get_docs(self, query):
        """
        Get documents (chunks) matching the query.

        Returns:
            tuple: (docs, chunk_ids) where:
                - docs: list of document content strings
                - chunk_ids: list of chunk IDs that were successfully fetched
        """
        vectors = await self.get_vector(query)

        if self.verbose:
            logger.debug("Getting chunks from embeddings store...")

        # Get chunk matches from embeddings store
        chunk_matches = await self.rag.doc_embeddings_client.query(
            vector=vectors, limit=self.doc_limit,
            user=self.user, collection=self.collection,
        )

        if self.verbose:
            logger.debug(f"Got {len(chunk_matches)} chunks, fetching content from Garage...")

        # Fetch chunk content from Garage
        docs = []
        chunk_ids = []
        for match in chunk_matches:
            if match.chunk_id:
                try:
                    content = await self.rag.fetch_chunk(match.chunk_id, self.user)
                    docs.append(content)
                    chunk_ids.append(match.chunk_id)
                except Exception as e:
                    logger.warning(f"Failed to fetch chunk {match.chunk_id}: {e}")

        if self.verbose:
            logger.debug("Documents fetched:")
            for doc in docs:
                logger.debug(f"  {doc[:100]}...")

        return docs, chunk_ids

class DocumentRag:

    def __init__(
            self, prompt_client, embeddings_client, doc_embeddings_client,
            fetch_chunk,
            verbose=False,
    ):

        self.verbose = verbose

        self.prompt_client = prompt_client
        self.embeddings_client = embeddings_client
        self.doc_embeddings_client = doc_embeddings_client
        self.fetch_chunk = fetch_chunk

        if self.verbose:
            logger.debug("DocumentRag initialized")

    async def query(
            self, query, user="trustgraph", collection="default",
            doc_limit=20, streaming=False, chunk_callback=None,
            explain_callback=None, save_answer_callback=None,
    ):
        """
        Execute a Document RAG query with optional explainability tracking.

        Args:
            query: The query string
            user: User identifier
            collection: Collection identifier
            doc_limit: Max chunks to retrieve
            streaming: Enable streaming LLM response
            chunk_callback: async def callback(chunk, end_of_stream) for streaming
            explain_callback: async def callback(triples, explain_id) for explainability
            save_answer_callback: async def callback(doc_id, answer_text) to save answer to librarian

        Returns:
            str: The synthesized answer text
        """
        if self.verbose:
            logger.debug("Constructing prompt...")

        # Generate explainability URIs upfront
        session_id = str(uuid.uuid4())
        q_uri = docrag_question_uri(session_id)
        exp_uri = docrag_exploration_uri(session_id)
        syn_uri = docrag_synthesis_uri(session_id)

        timestamp = datetime.utcnow().isoformat() + "Z"

        # Emit question explainability immediately
        if explain_callback:
            q_triples = set_graph(
                docrag_question_triples(q_uri, query, timestamp),
                GRAPH_RETRIEVAL
            )
            await explain_callback(q_triples, q_uri)

        q = Query(
            rag=self, user=user, collection=collection, verbose=self.verbose,
            doc_limit=doc_limit
        )

        docs, chunk_ids = await q.get_docs(query)

        # Emit exploration explainability after chunks retrieved
        if explain_callback:
            exp_triples = set_graph(
                docrag_exploration_triples(exp_uri, q_uri, len(chunk_ids), chunk_ids),
                GRAPH_RETRIEVAL
            )
            await explain_callback(exp_triples, exp_uri)

        if self.verbose:
            logger.debug("Invoking LLM...")
            logger.debug(f"Documents: {docs}")
            logger.debug(f"Query: {query}")

        if streaming and chunk_callback:
            # Accumulate chunks for answer storage while forwarding to callback
            accumulated_chunks = []

            async def accumulating_callback(chunk, end_of_stream):
                accumulated_chunks.append(chunk)
                await chunk_callback(chunk, end_of_stream)

            resp = await self.prompt_client.document_prompt(
                query=query,
                documents=docs,
                streaming=True,
                chunk_callback=accumulating_callback
            )
            # Combine all chunks into full response
            resp = "".join(accumulated_chunks)
        else:
            resp = await self.prompt_client.document_prompt(
                query=query,
                documents=docs
            )

        if self.verbose:
            logger.debug("Query processing complete")

        # Emit synthesis explainability after answer generated
        if explain_callback:
            synthesis_doc_id = None
            answer_text = resp if resp else ""

            # Save answer to librarian if callback provided
            if save_answer_callback and answer_text:
                # Generate document ID as URN matching query-time provenance format
                synthesis_doc_id = f"urn:trustgraph:docrag:{session_id}/answer"
                try:
                    await save_answer_callback(synthesis_doc_id, answer_text)
                    if self.verbose:
                        logger.debug(f"Saved answer to librarian: {synthesis_doc_id}")
                except Exception as e:
                    logger.warning(f"Failed to save answer to librarian: {e}")
                    synthesis_doc_id = None  # Fall back to inline content

            # Generate triples with document reference or inline content
            syn_triples = set_graph(
                docrag_synthesis_triples(
                    syn_uri, exp_uri,
                    answer_text="" if synthesis_doc_id else answer_text,
                    document_id=synthesis_doc_id,
                ),
                GRAPH_RETRIEVAL
            )
            await explain_callback(syn_triples, syn_uri)

        if self.verbose:
            logger.debug(f"Emitted explain for session {session_id}")

        return resp

