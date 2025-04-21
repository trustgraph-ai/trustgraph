
import asyncio

LABEL="http://www.w3.org/2000/01/rdf-schema#label"
DEFINITION="http://www.w3.org/2004/02/skos/core#definition"

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
            print("Compute embeddings...", flush=True)

        qembeds = await  self.rag.embeddings_client.embed(query)

        if self.verbose:
            print("Done.", flush=True)

        return qembeds

    async def get_entities(self, query):

        vectors = await self.get_vector(query)

        if self.verbose:
            print("Get entities...", flush=True)

        entities = await self.rag.graph_embeddings_client.query(
            vectors=vectors, limit=self.entity_limit,
            user=self.user, collection=self.collection,
        )

        print("ENT>", entities, flush=True)

        entities = [
            e.value
            for e in entities
        ]

        if self.verbose:
            print("Entities:", flush=True)
            for ent in entities:
                print(" ", ent, flush=True)

        return entities
        
    async def maybe_label(self, e):

        if e in self.rag.label_cache:
            return self.rag.label_cache[e]

        res = await self.rag.triples_client.request(
            user=self.user, collection=self.collection,
            s=e, p=LABEL, o=None, limit=1,
        )

        if len(res) == 0:
            self.rag.label_cache[e] = e
            return e

        self.rag.label_cache[e] = res[0].o.value
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
                (triple.s.value, triple.p.value, triple.o.value)
            )
            if path_length > 1:
                await self.follow_edges(triple.o.value, subgraph, path_length-1)

        res = await self.rag.triples_client.request(
            user=self.user, collection=self.collection,
            s=None, p=ent, o=None,
            limit=self.triple_limit
        )

        for triple in res:
            subgraph.add(
                (triple.s.value, triple.p.value, triple.o.value)
            )

        res = await self.rag.triples_client.request(
            user=self.user, collection=self.collection,
            s=None, p=None, o=ent,
            limit=self.triple_limit,
        )

        for triple in res:
            subgraph.add(
                (triple.s.value, triple.p.value, triple.o.value)
            )
            if path_length > 1:
                await self.follow_edges(triple.s.value, subgraph, path_length-1)

    async def get_subgraph(self, query):

        entities = await self.get_entities(query)

        if self.verbose:
            print("Get subgraph...", flush=True)

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
            print("Subgraph:", flush=True)
            for edge in sg2:
                print(" ", str(edge), flush=True)

        if self.verbose:
            print("Done.", flush=True)

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
            print("Initialised", flush=True)

    async def query(
            self, query, user = "trustgraph", collection = "default",
            entity_limit = 50, triple_limit = 30, max_subgraph_size = 1000,
            max_path_length = 2,
    ):

        if self.verbose:
            print("Construct prompt...", flush=True)

        q = Query(
            rag = self, user = user, collection = collection,
            verbose = self.verbose, entity_limit = entity_limit,
            triple_limit = triple_limit,
            max_subgraph_size = max_subgraph_size,
            max_path_length = max_path_length,
        )

        kg = await q.get_labelgraph(query)

        if self.verbose:
            print("Invoke LLM...", flush=True)
            print(kg)
            print(query)

        resp = await self.prompt_client.request_kg_prompt(query, kg)

        if self.verbose:
            print("Done", flush=True)

        return resp

