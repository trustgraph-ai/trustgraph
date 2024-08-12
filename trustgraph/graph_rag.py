
from trustgraph.trustgraph import TrustGraph
from trustgraph.triple_vectors import TripleVectors
from trustgraph.trustgraph import TrustGraph
from trustgraph.llm_client import LlmClient
from trustgraph.embeddings_client import EmbeddingsClient
from . schema import text_completion_request_queue
from . schema import text_completion_response_queue
from . schema import embeddings_request_queue
from . schema import embeddings_response_queue

LABEL="http://www.w3.org/2000/01/rdf-schema#label"
DEFINITION="http://www.w3.org/2004/02/skos/core#definition"

class GraphRag:

    def __init__(
            self,
            graph_hosts=None,
            pulsar_host="pulsar://pulsar:6650",
            vector_store="http://milvus:19530",
            completion_request_queue=None,
            completion_response_queue=None,
            emb_request_queue=None,
            emb_response_queue=None,
            verbose=False,
            entity_limit=50,
            triple_limit=30,
            max_subgraph_size=3000,
            module="test",
    ):

        self.verbose=verbose

        if completion_request_queue == None:
            completion_request_queue = text_completion_request_queue

        if completion_response_queue == None:
            completion_response_queue = text_completion_response_queue

        if emb_request_queue == None:
            emb_request_queue = embeddings_request_queue

        if emb_response_queue == None:
            emb_response_queue = embeddings_response_queue

        if graph_hosts == None:
            graph_hosts = ["cassandra"]

        if self.verbose:
            print("Initialising...", flush=True)

        self.graph = TrustGraph(graph_hosts)

        self.embeddings = EmbeddingsClient(
            pulsar_host=pulsar_host,
            input_queue=emb_request_queue,
            output_queue=emb_response_queue,
            subscriber=module + "-emb",
        )

        self.vecstore = TripleVectors(vector_store)

        self.entity_limit=entity_limit
        self.query_limit=triple_limit
        self.max_subgraph_size=max_subgraph_size

        self.label_cache = {}

        self.llm = LlmClient(
            pulsar_host=pulsar_host,
            input_queue=completion_request_queue,
            output_queue=completion_response_queue,
            subscriber=module + "-llm",
        )

        if self.verbose:
            print("Initialised", flush=True)

    def get_vector(self, query):

        if self.verbose:
            print("Compute embeddings...", flush=True)

        qembeds = self.embeddings.request(query)

        if self.verbose:
            print("Done.", flush=True)

        return qembeds

    def get_entities(self, query):

        everything = []

        vectors = self.get_vector(query)

        if self.verbose:
            print("Get entities...", flush=True)

        for vector in vectors:

            res = self.vecstore.search(
                vector,
                limit=self.entity_limit
            )

            print("Obtained", len(res), "entities")

            entities = set([
                item["entity"]["entity"]
                for item in res
            ])

            everything.extend(entities)

        if self.verbose:
            print("Entities:", flush=True)
            for ent in everything:
                print(" ", ent, flush=True)

        return everything
        
    def maybe_label(self, e):

        if e in self.label_cache:
            return self.label_cache[e]

        res = self.graph.get_sp(e, LABEL)
        res = list(res)

        if len(res) == 0:
            self.label_cache[e] = e
            return e

        self.label_cache[e] = res[0][0]
        return self.label_cache[e]

    def get_nodes(self, query):

        ents = self.get_entities(query)

        if self.verbose:
            print("Get labels...", flush=True)

        nodes = [
            self.maybe_label(e)
            for e in ents
        ]

        if self.verbose:
            print("Nodes:", flush=True)
            for node in nodes:
                print(" ", node, flush=True)

        return nodes

    def get_subgraph(self, query):

        entities = self.get_entities(query)

        subgraph = set()

        if self.verbose:
            print("Get subgraph...", flush=True)

        for e in entities:

            res = self.graph.get_s(e, limit=self.query_limit)
            for p, o in res:
                subgraph.add((e, p, o))

            res = self.graph.get_p(e, limit=self.query_limit)
            for s, o in res:
                subgraph.add((s, e, o))

            res = self.graph.get_o(e, limit=self.query_limit)
            for s, p in res:
                subgraph.add((s, p, e))

        subgraph = list(subgraph)

        subgraph = subgraph[0:self.max_subgraph_size]

        if self.verbose:
            print("Subgraph:", flush=True)
            for edge in subgraph:
                print(" ", str(edge), flush=True)

        if self.verbose:
            print("Done.", flush=True)

        return subgraph

    def get_labelgraph(self, query):

        subgraph = self.get_subgraph(query)

        sg2 = []

        for edge in subgraph:

            if edge[1] == LABEL:
                continue

            s = self.maybe_label(edge[0])
            p = self.maybe_label(edge[1])
            o = self.maybe_label(edge[2])

            sg2.append((s, p, o))

        return sg2

    def get_cypher(self, query):

        sg = self.get_labelgraph(query)

        sg2 = []

        for s, p, o in sg:

            sg2.append(f"({s})-[{p}]->({o})")

        kg = "\n".join(sg2)
        kg = kg.replace("\\", "-")

        return kg

    def get_graph_prompt(self, query):

        kg =  self.get_cypher(query)

        prompt=f"""Study the following set of knowledge statements. The statements are written in Cypher format that has been extracted from a knowledge graph. Use only the provided set of knowledge statements in your response. Do not speculate if the answer is not found in the provided set of knowledge statements.

Here's the knowledge statements:
{kg}

Use only the provided knowledge statements to respond to the following:
{query}
"""

        return prompt

    def query(self, query):

        if self.verbose:
            print("Construct prompt...", flush=True)

        prompt = self.get_graph_prompt(query)

        if self.verbose:
            print("Invoke LLM...", flush=True)

        resp = self.llm.request(prompt)

        if self.verbose:
            print("Done", flush=True)

        return resp

