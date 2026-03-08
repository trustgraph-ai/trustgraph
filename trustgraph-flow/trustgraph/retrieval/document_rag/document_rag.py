
import asyncio
import logging

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

        vectors = await self.get_vector(query)

        if self.verbose:
            logger.debug("Getting chunk_ids from embeddings store...")

        # Get chunk_ids from embeddings store
        chunk_ids = await self.rag.doc_embeddings_client.query(
            vectors, limit=self.doc_limit,
            user=self.user, collection=self.collection,
        )

        if self.verbose:
            logger.debug(f"Got {len(chunk_ids)} chunk_ids, fetching content from Garage...")

        # Fetch chunk content from Garage
        docs = []
        for chunk_id in chunk_ids:
            if chunk_id:
                try:
                    content = await self.rag.fetch_chunk(chunk_id, self.user)
                    docs.append(content)
                except Exception as e:
                    logger.warning(f"Failed to fetch chunk {chunk_id}: {e}")

        if self.verbose:
            logger.debug("Documents fetched:")
            for doc in docs:
                logger.debug(f"  {doc[:100]}...")

        return docs

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
    ):

        if self.verbose:
            logger.debug("Constructing prompt...")

        q = Query(
            rag=self, user=user, collection=collection, verbose=self.verbose,
            doc_limit=doc_limit
        )

        docs = await q.get_docs(query)

        if self.verbose:
            logger.debug("Invoking LLM...")
            logger.debug(f"Documents: {docs}")
            logger.debug(f"Query: {query}")

        if streaming and chunk_callback:
            resp = await self.prompt_client.document_prompt(
                query=query,
                documents=docs,
                streaming=True,
                chunk_callback=chunk_callback
            )
        else:
            resp = await self.prompt_client.document_prompt(
                query=query,
                documents=docs
            )

        if self.verbose:
            logger.debug("Query processing complete")

        return resp

