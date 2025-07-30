
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

        qembeds = await  self.rag.embeddings_client.embed(query)

        if self.verbose:
            logger.debug("Embeddings computed")

        return qembeds

    async def get_docs(self, query):

        vectors = await self.get_vector(query)

        if self.verbose:
            logger.debug("Getting documents...")

        docs = await self.rag.doc_embeddings_client.query(
            vectors, limit=self.doc_limit,
            user=self.user, collection=self.collection,
        )

        if self.verbose:
            logger.debug("Documents:")
            for doc in docs:
                logger.debug(f"  {doc}")

        return docs

class DocumentRag:

    def __init__(
            self, prompt_client, embeddings_client, doc_embeddings_client,
            verbose=False,
    ):

        self.verbose = verbose

        self.prompt_client = prompt_client
        self.embeddings_client = embeddings_client
        self.doc_embeddings_client = doc_embeddings_client

        if self.verbose:
            logger.debug("DocumentRag initialized")

    async def query(
            self, query, user="trustgraph", collection="default",
            doc_limit=20,
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

        resp = await self.prompt_client.document_prompt(
            query = query,
            documents = docs
        )

        if self.verbose:
            logger.debug("Query processing complete")

        return resp

