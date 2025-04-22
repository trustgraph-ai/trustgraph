
import asyncio

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
            print("Compute embeddings...", flush=True)

        qembeds = await  self.rag.embeddings_client.embed(query)

        if self.verbose:
            print("Done.", flush=True)

        return qembeds

    async def get_docs(self, query):

        vectors = await self.get_vector(query)

        if self.verbose:
            print("Get docs...", flush=True)

        docs = await self.rag.doc_embeddings_client.query(
            vectors, limit=self.doc_limit,
            user=self.user, collection=self.collection,
        )

        if self.verbose:
            print("Docs:", flush=True)
            for doc in docs:
                print(doc, flush=True)

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
            print("Initialised", flush=True)

    async def query(
            self, query, user="trustgraph", collection="default",
            doc_limit=20,
    ):

        if self.verbose:
            print("Construct prompt...", flush=True)

        q = Query(
            rag=self, user=user, collection=collection, verbose=self.verbose,
            doc_limit=doc_limit
        )

        docs = await q.get_docs(query)

        if self.verbose:
            print("Invoke LLM...", flush=True)
            print(docs)
            print(query)

        resp = await self.prompt_client.document_prompt(
            query = query,
            documents = docs
        )

        if self.verbose:
            print("Done", flush=True)

        return resp

