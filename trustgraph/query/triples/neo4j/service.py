
"""
Triples query service.  Input is a (s, p, o) triple, some values may be
null.  Output is a list of triples.
"""

from neo4j import GraphDatabase

from .... schema import TriplesQueryRequest, TriplesQueryResponse
from .... schema import Value, Triple
from .... schema import triples_request_queue
from .... schema import triples_response_queue
from .... base import ConsumerProducer

module = ".".join(__name__.split(".")[1:-1])

default_input_queue = triples_request_queue
default_output_queue = triples_response_queue
default_subscriber = module

default_graph_host = 'bolt://localhost:7687'
default_username = 'neo4j'
default_password = 'password'

class Processor(ConsumerProducer):

    def __init__(self, **params):

        input_queue = params.get("input_queue", default_input_queue)
        output_queue = params.get("output_queue", default_output_queue)
        subscriber = params.get("subscriber", default_subscriber)
        graph_host = params.get("graph_host", default_graph_host)
        username = params.get("username", default_username)
        password = params.get("passowrd", default_password)

        super(Processor, self).__init__(
            **params | {
                "input_queue": input_queue,
                "output_queue": output_queue,
                "subscriber": subscriber,
                "input_schema": TriplesQueryRequest,
                "output_schema": TriplesQueryResponse,
                "graph_host": graph_host,
            }
        )

        self.db = "neo4j"

        self.io = GraphDatabase.driver(graph_host, auth=(username, password))

    def create_value(self, ent):

        if ent.startswith("http://") or ent.startswith("https://"):
            return Value(value=ent, is_uri=True)
        else:
            return Value(value=ent, is_uri=False)

    def handle(self, msg):

        v = msg.value()

        # Sender-produced ID
        id = msg.properties()["id"]

        print(f"Handling input {id}...", flush=True)

        triples = []

        if v.s is not None:
            if v.p is not None:
                if v.o is not None:

                    # SPO

                    records, summary, keys = self.io.execute_query(
                        "MATCH (src:Node {uri: $src})-[rel:Rel {uri: $rel}]->(dest:Literal {value: $value}) "
                        "RETURN $src as src",
                        src=v.s.value, rel=v.p.value, value=v.o.value,
                        database_=self.db,
                    )

                    for rec in records:
                        triples.append((v.s.value, v.p.value, v.o.value))
                    
                    records, summary, keys = self.io.execute_query(
                        "MATCH (src:Node {uri: $src})-[rel:Rel {uri: $rel}]->(dest:Node {uri: $uri}) "
                        "RETURN $src as src",
                        src=v.s.value, rel=v.p.value, uri=v.o.value,
                        database_=self.db,
                    )

                    for rec in records:
                        triples.append((v.s.value, v.p.value, v.o.value))

                else:

                    # SP
                    
                    records, summary, keys = self.io.execute_query(
                        "MATCH (src:Node {uri: $src})-[rel:Rel {uri: $rel}]->(dest:Literal) "
                        "RETURN dest.value as dest",
                        src=v.s.value, rel=v.p.value,
                        database_=self.db,
                    )

                    for rec in records:
                        data = rec.data()
                        triples.append((v.s.value, v.p.value, data["dest"]))
                    
                    records, summary, keys = self.io.execute_query(
                        "MATCH (src:Node {uri: $src})-[rel:Rel {uri: $rel}]->(dest:Node) "
                        "RETURN dest.uri as dest",
                        src=v.s.value, rel=v.p.value,
                        database_=self.db,
                    )

                    for rec in records:
                        data = rec.data()
                        triples.append((v.s.value, v.p.value, data["dest"]))

            else:

                if v.o is not None:

                    # SO

                    records, summary, keys = self.io.execute_query(
                        "MATCH (src:Node {uri: $src})-[rel:Rel]->(dest:Literal {value: $value}) "
                        "RETURN rel.uri as rel",
                        src=v.s.value, value=v.o.value,
                        database_=self.db,
                    )

                    for rec in records:
                        data = rec.data()
                        triples.append((v.s.value, data["rel"], v.o.value))
                    
                    records, summary, keys = self.io.execute_query(
                        "MATCH (src:Node {uri: $src})-[rel:Rel]->(dest:Node {uri: $uri}) "
                        "RETURN rel.uri as rel",
                        src=v.s.value, uri=v.o.value,
                        database_=self.db,
                    )

                    for rec in records:
                        data = rec.data()
                        triples.append((v.s.value, data["rel"], v.o.value))

                else:

                    # S

                    records, summary, keys = self.io.execute_query(
                        "MATCH (src:Node {uri: $src})-[rel:Rel]->(dest:Literal) "
                        "RETURN rel.uri as rel, dest.value as dest",
                        src=v.s.value,
                        database_=self.db,
                    )

                    for rec in records:
                        data = rec.data()
                        triples.append((v.s.value, data["rel"], data["dest"]))
                    
                    records, summary, keys = self.io.execute_query(
                        "MATCH (src:Node {uri: $src})-[rel:Rel]->(dest:Node) "
                        "RETURN rel.uri as rel, dest.uri as dest",
                        src=v.s.value,
                        database_=self.db,
                    )

                    for rec in records:
                        data = rec.data()
                        triples.append((v.s.value, data["rel"], data["dest"]))


        else:

            if v.p is not None:

                if v.o is not None:

                    # PO
                    pass

                else:

                    # P
                    pass

            else:

                if v.o is not None:

                    # O
                    pass

                else:

                    # *
                    pass

        triples = [
            Triple(
                s=self.create_value(t[0]),
                p=self.create_value(t[1]), 
                o=self.create_value(t[2])
            )
            for t in triples
        ]

        print("Send response...", flush=True)
        r = TriplesQueryResponse(triples=triples)
        self.producer.send(r, properties={"id": id})

        print("Done.", flush=True)

    @staticmethod
    def add_args(parser):

        ConsumerProducer.add_args(
            parser, default_input_queue, default_subscriber,
            default_output_queue,
        )

        parser.add_argument(
            '-g', '--graph-host',
            default=default_graph_host,
            help=f'Graph host (default: {default_graph_host})'
        )

        parser.add_argument(
            '--username',
            default=default_username,
            help=f'Neo4j username (default: {default_username})'
        )

        parser.add_argument(
            '--password',
            default=default_password,
            help=f'Neo4j password (default: {default_password})'
        )

def run():

    Processor.start(module, __doc__)

