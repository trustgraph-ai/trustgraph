
import asyncio
import logging

# Module logger
logger = logging.getLogger(__name__)

LABEL="http://www.w3.org/2000/01/rdf-schema#label"

class Query:

    def __init__(
            self, rag, user, collection, verbose,
            entity_limit=50, triple_limit=30, max_subgraph_size=1000,
            max_path_length=2,
    ):
        self.rag = rag
        self.user = user
        self.collection = collection
        self.verbose = verbose
        self.entity_limit = entity_limit
        self.triple_limit = triple_limit
        self.max_subgraph_size = max_subgraph_size
        self.max_path_length = max_path_length

    async def get_vector(self, query):

        if self.verbose:
            logger.debug("Computing embeddings...")

        qembeds = await  self.rag.embeddings_client.embed(query)

        if self.verbose:
            logger.debug("Done.")

        return qembeds

    async def get_entities(self, query):

        vectors = await self.get_vector(query)

        if self.verbose:
            logger.debug("Getting entities...")

        entities = await self.rag.graph_embeddings_client.query(
            vectors=vectors, limit=self.entity_limit,
            user=self.user, collection=self.collection,
        )

        entities = [
            str(e)
            for e in entities
        ]

        if self.verbose:
            logger.debug("Entities:")
            for ent in entities:
                logger.debug(f"  {ent}")

        return entities
        
    async def maybe_label(self, e):

        if e in self.rag.label_cache:
            return self.rag.label_cache[e]

        res = await self.rag.triples_client.query(
            s=e, p=LABEL, o=None, limit=1,
            user=self.user, collection=self.collection,
        )

        if len(res) == 0:
            self.rag.label_cache[e] = e
            return e

        self.rag.label_cache[e] = str(res[0].o)
        return self.rag.label_cache[e]

    async def follow_edges(self, ent, subgraph, path_length):

        # Not needed?
        if path_length <= 0:
            return

        # Stop spanning around if the subgraph is already maxed out
        if len(subgraph) >= self.max_subgraph_size:
            return

        res = await self.rag.triples_client.query(
            s=ent, p=None, o=None,
            limit=self.triple_limit,
            user=self.user, collection=self.collection,
        )

        for triple in res:
            subgraph.add(
                (str(triple.s), str(triple.p), str(triple.o))
            )
            if path_length > 1:
                await self.follow_edges(str(triple.o), subgraph, path_length-1)

        res = await self.rag.triples_client.query(
            s=None, p=ent, o=None,
            limit=self.triple_limit,
            user=self.user, collection=self.collection,
        )

        for triple in res:
            subgraph.add(
                (str(triple.s), str(triple.p), str(triple.o))
            )

        res = await self.rag.triples_client.query(
            s=None, p=None, o=ent,
            limit=self.triple_limit,
            user=self.user, collection=self.collection,
        )

        for triple in res:
            subgraph.add(
                (str(triple.s), str(triple.p), str(triple.o))
            )
            if path_length > 1:
                await self.follow_edges(
                    str(triple.s), subgraph, path_length-1
                )

    async def get_subgraph(self, query):

        entities = await self.get_entities(query)

        if self.verbose:
            logger.debug("Getting subgraph...")

        subgraph = set()

        for ent in entities:
            await self.follow_edges(ent, subgraph, self.max_path_length)

        subgraph = list(subgraph)

        return subgraph

    async def get_labelgraph(self, query):

        subgraph = await self.get_subgraph(query)

        sg2 = []

        for edge in subgraph:

            if edge[1] == LABEL:
                continue

            s = await self.maybe_label(edge[0])
            p = await self.maybe_label(edge[1])
            o = await self.maybe_label(edge[2])

            sg2.append((s, p, o))

        sg2 = sg2[0:self.max_subgraph_size]

        if self.verbose:
            logger.debug("Subgraph:")
            for edge in sg2:
                logger.debug(f"  {str(edge)}")

        if self.verbose:
            logger.debug("Done.")

        return sg2
    
class GraphRag:

    def __init__(
            self, prompt_client, embeddings_client, graph_embeddings_client,
            triples_client, verbose=False,
    ):

        self.verbose = verbose

        self.prompt_client = prompt_client
        self.embeddings_client = embeddings_client
        self.graph_embeddings_client = graph_embeddings_client
        self.triples_client = triples_client

        self.label_cache = {}

        if self.verbose:
            logger.debug("GraphRag initialized")

    async def query(
            self, query, user = "trustgraph", collection = "default",
            entity_limit = 50, triple_limit = 30, max_subgraph_size = 1000,
            max_path_length = 2,
    ):

        if self.verbose:
            logger.debug("Constructing prompt...")

        q = Query(
            rag = self, user = user, collection = collection,
            verbose = self.verbose, entity_limit = entity_limit,
            triple_limit = triple_limit,
            max_subgraph_size = max_subgraph_size,
            max_path_length = max_path_length,
        )

        kg = await q.get_labelgraph(query)

        if self.verbose:
            logger.debug("Invoking LLM...")
            logger.debug(f"Knowledge graph: {kg}")
            logger.debug(f"Query: {query}")

        resp = await self.prompt_client.kg_prompt(query, kg)

        if self.verbose:
            logger.debug("Query processing complete")

        return resp

