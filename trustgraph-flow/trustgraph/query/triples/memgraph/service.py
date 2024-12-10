
"""
Triples query service for memgraph.
Input is a (s, p, o) triple, some values may be null.  Output is a list of
triples.
"""

from neo4j import GraphDatabase

from .... schema import TriplesQueryRequest, TriplesQueryResponse, Error
from .... schema import Value, Triple
from .... schema import triples_request_queue
from .... schema import triples_response_queue
from .... base import ConsumerProducer

module = ".".join(__name__.split(".")[1:-1])

default_input_queue = triples_request_queue
default_output_queue = triples_response_queue
default_subscriber = module

default_graph_host = 'bolt://memgraph:7687'
default_username = 'memgraph'
default_password = 'password'
default_database = 'memgraph'

class Processor(ConsumerProducer):

    def __init__(self, **params):

        input_queue = params.get("input_queue", default_input_queue)
        output_queue = params.get("output_queue", default_output_queue)
        subscriber = params.get("subscriber", default_subscriber)
        graph_host = params.get("graph_host", default_graph_host)
        username = params.get("username", default_username)
        password = params.get("password", default_password)
        database = params.get("database", default_database)

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

        self.db = database

        self.io = GraphDatabase.driver(graph_host, auth=(username, password))

    def create_value(self, ent):

        if ent.startswith("http://") or ent.startswith("https://"):
            return Value(value=ent, is_uri=True)
        else:
            return Value(value=ent, is_uri=False)

    def handle(self, msg):

        try:

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
                            "RETURN $src as src "
                            "LIMIT " + str(v.limit),
                            src=v.s.value, rel=v.p.value, value=v.o.value,
                            database_=self.db,
                        )

                        for rec in records:
                            triples.append((v.s.value, v.p.value, v.o.value))

                        records, summary, keys = self.io.execute_query(
                            "MATCH (src:Node {uri: $src})-[rel:Rel {uri: $rel}]->(dest:Node {uri: $uri}) "
                            "RETURN $src as src "
                            "LIMIT " + str(v.limit),
                            src=v.s.value, rel=v.p.value, uri=v.o.value,
                            database_=self.db,
                        )

                        for rec in records:
                            triples.append((v.s.value, v.p.value, v.o.value))

                    else:

                        # SP

                        records, summary, keys = self.io.execute_query(
                            "MATCH (src:Node {uri: $src})-[rel:Rel {uri: $rel}]->(dest:Literal) "
                            "RETURN dest.value as dest "
                            "LIMIT " + str(v.limit),
                            src=v.s.value, rel=v.p.value,
                            database_=self.db,
                        )

                        for rec in records:
                            data = rec.data()
                            triples.append((v.s.value, v.p.value, data["dest"]))

                        records, summary, keys = self.io.execute_query(
                            "MATCH (src:Node {uri: $src})-[rel:Rel {uri: $rel}]->(dest:Node) "
                            "RETURN dest.uri as dest "
                            "LIMIT " + str(v.limit),
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
                            "RETURN rel.uri as rel "
                            "LIMIT " + str(v.limit),
                            src=v.s.value, value=v.o.value,
                            database_=self.db,
                        )

                        for rec in records:
                            data = rec.data()
                            triples.append((v.s.value, data["rel"], v.o.value))

                        records, summary, keys = self.io.execute_query(
                            "MATCH (src:Node {uri: $src})-[rel:Rel]->(dest:Node {uri: $uri}) "
                            "RETURN rel.uri as rel "
                            "LIMIT " + str(v.limit),
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
                            "RETURN rel.uri as rel, dest.value as dest "
                            "LIMIT " + str(v.limit),
                            src=v.s.value,
                            database_=self.db,
                        )

                        for rec in records:
                            data = rec.data()
                            triples.append((v.s.value, data["rel"], data["dest"]))

                        records, summary, keys = self.io.execute_query(
                            "MATCH (src:Node {uri: $src})-[rel:Rel]->(dest:Node) "
                            "RETURN rel.uri as rel, dest.uri as dest "
                            "LIMIT " + str(v.limit),
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

                        records, summary, keys = self.io.execute_query(
                            "MATCH (src:Node)-[rel:Rel {uri: $uri}]->(dest:Literal {value: $value}) "
                            "RETURN src.uri as src "
                            "LIMIT " + str(v.limit),
                            uri=v.p.value, value=v.o.value,
                            database_=self.db,
                        )

                        for rec in records:
                            data = rec.data()
                            triples.append((data["src"], v.p.value, v.o.value))

                        records, summary, keys = self.io.execute_query(
                            "MATCH (src:Node)-[rel:Rel {uri: $uri}]->(dest:Node {uri: $uri}) "
                            "RETURN src.uri as src "
                            "LIMIT " + str(v.limit),
                            uri=v.p.value, dest=v.o.value,
                            database_=self.db,
                        )

                        for rec in records:
                            data = rec.data()
                            triples.append((data["src"], v.p.value, v.o.value))

                    else:

                        # P

                        records, summary, keys = self.io.execute_query(
                            "MATCH (src:Node)-[rel:Rel {uri: $uri}]->(dest:Literal) "
                            "RETURN src.uri as src, dest.value as dest "
                            "LIMIT " + str(v.limit),
                            uri=v.p.value,
                            database_=self.db,
                        )

                        for rec in records:
                            data = rec.data()
                            triples.append((data["src"], v.p.value, data["dest"]))

                        records, summary, keys = self.io.execute_query(
                            "MATCH (src:Node)-[rel:Rel {uri: $uri}]->(dest:Node) "
                            "RETURN src.uri as src, dest.uri as dest "
                            "LIMIT " + str(v.limit),
                            uri=v.p.value,
                            database_=self.db,
                        )

                        for rec in records:
                            data = rec.data()
                            triples.append((data["src"], v.p.value, data["dest"]))

                else:

                    if v.o is not None:

                        # O

                        records, summary, keys = self.io.execute_query(
                            "MATCH (src:Node)-[rel:Rel]->(dest:Literal {value: $value}) "
                            "RETURN src.uri as src, rel.uri as rel "
                            "LIMIT " + str(v.limit),
                            value=v.o.value,
                            database_=self.db,
                        )

                        for rec in records:
                            data = rec.data()
                            triples.append((data["src"], data["rel"], v.o.value))

                        records, summary, keys = self.io.execute_query(
                            "MATCH (src:Node)-[rel:Rel]->(dest:Node {uri: $uri}) "
                            "RETURN src.uri as src, rel.uri as rel "
                            "LIMIT " + str(v.limit),
                            uri=v.o.value,
                            database_=self.db,
                        )

                        for rec in records:
                            data = rec.data()
                            triples.append((data["src"], data["rel"], v.o.value))

                    else:

                        # *

                        records, summary, keys = self.io.execute_query(
                            "MATCH (src:Node)-[rel:Rel]->(dest:Literal) "
                            "RETURN src.uri as src, rel.uri as rel, dest.value as dest "
                            "LIMIT " + str(v.limit),
                            database_=self.db,
                        )

                        for rec in records:
                            data = rec.data()
                            triples.append((data["src"], data["rel"], data["dest"]))

                        records, summary, keys = self.io.execute_query(
                            "MATCH (src:Node)-[rel:Rel]->(dest:Node) "
                            "RETURN src.uri as src, rel.uri as rel, dest.uri as dest "
                            "LIMIT " + str(v.limit),
                            database_=self.db,
                        )

                        for rec in records:
                            data = rec.data()
                            triples.append((data["src"], data["rel"], data["dest"]))

            triples = [
                Triple(
                    s=self.create_value(t[0]),
                    p=self.create_value(t[1]), 
                    o=self.create_value(t[2])
                )
                for t in triples[:v.limit]
            ]

            print("Send response...", flush=True)
            r = TriplesQueryResponse(triples=triples, error=None)
            self.producer.send(r, properties={"id": id})

            print("Done.", flush=True)

        except Exception as e:

            print(f"Exception: {e}")

            print("Send error response...", flush=True)

            r = TriplesQueryResponse(
                error=Error(
                    type = "llm-error",
                    message = str(e),
                ),
                response=None,
            )

            self.producer.send(r, properties={"id": id})

            self.consumer.acknowledge(msg)
            
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
            help=f'Memgraph username (default: {default_username})'
        )

        parser.add_argument(
            '--password',
            default=default_password,
            help=f'Memgraph password (default: {default_password})'
        )

        parser.add_argument(
            '--database',
            default=default_database,
            help=f'Memgraph database (default: {default_database})'
        )

def run():

    Processor.start(module, __doc__)

