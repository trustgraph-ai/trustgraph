
"""
Triples query service.  Input is a (s, p, o) triple, some values may be
null.  Output is a list of triples.
"""

from .... direct.cassandra import TrustGraph
from .... schema import TriplesQueryRequest, TriplesQueryResponse, Error
from .... schema import Value, Triple
from .... schema import triples_request_queue
from .... schema import triples_response_queue
from .... base import ConsumerProducer

module = "triples-query"

default_input_queue = triples_request_queue
default_output_queue = triples_response_queue
default_subscriber = module
default_graph_host='localhost'

class Processor(ConsumerProducer):

    def __init__(self, **params):

        input_queue = params.get("input_queue", default_input_queue)
        output_queue = params.get("output_queue", default_output_queue)
        subscriber = params.get("subscriber", default_subscriber)
        graph_host = params.get("graph_host", default_graph_host)
        graph_username = params.get("graph_username", None)
        graph_password = params.get("graph_password", None)

        super(Processor, self).__init__(
            **params | {
                "input_queue": input_queue,
                "output_queue": output_queue,
                "subscriber": subscriber,
                "input_schema": TriplesQueryRequest,
                "output_schema": TriplesQueryResponse,
                "graph_host": graph_host,
                "graph_username": graph_username,
                "graph_password": graph_password,
            }
        )

        self.graph_host = [graph_host]
        self.username = graph_username
        self.password = graph_password
        self.table = None

    def create_value(self, ent):
        if ent.startswith("http://") or ent.startswith("https://"):
            return Value(value=ent, is_uri=True)
        else:
            return Value(value=ent, is_uri=False)

    async def handle(self, msg):

        try:

            v = msg.value()

            table = (v.user, v.collection)

            if table != self.table:
                if self.username and self.password:
                    self.tg = TrustGraph(
                        hosts=self.graph_host,
                        keyspace=v.user, table=v.collection,
                        username=self.username, password=self.password
                    )
                else:
                    self.tg = TrustGraph(
                        hosts=self.graph_host,
                        keyspace=v.user, table=v.collection,
                    )
                self.table = table

            # Sender-produced ID
            id = msg.properties()["id"]

            print(f"Handling input {id}...", flush=True)

            triples = []

            if v.s is not None:
                if v.p is not None:
                    if v.o is not None:
                        resp = self.tg.get_spo(
                            v.s.value, v.p.value, v.o.value,
                            limit=v.limit
                        )
                        triples.append((v.s.value, v.p.value, v.o.value))
                    else:
                        resp = self.tg.get_sp(
                            v.s.value, v.p.value,
                            limit=v.limit
                        )
                        for t in resp:
                            triples.append((v.s.value, v.p.value, t.o))
                else:
                    if v.o is not None:
                        resp = self.tg.get_os(
                            v.o.value, v.s.value, 
                            limit=v.limit
                        )
                        for t in resp:
                            triples.append((v.s.value, t.p, v.o.value))
                    else:
                        resp = self.tg.get_s(
                            v.s.value,
                            limit=v.limit
                        )
                        for t in resp:
                            triples.append((v.s.value, t.p, t.o))
            else:
                if v.p is not None:
                    if v.o is not None:
                        resp = self.tg.get_po(
                            v.p.value, v.o.value,
                            limit=v.limit
                        )
                        for t in resp:
                            triples.append((t.s, v.p.value, v.o.value))
                    else:
                        resp = self.tg.get_p(
                            v.p.value,
                            limit=v.limit
                        )
                        for t in resp:
                            triples.append((t.s, v.p.value, t.o))
                else:
                    if v.o is not None:
                        resp = self.tg.get_o(
                            v.o.value,
                            limit=v.limit
                        )
                        for t in resp:
                            triples.append((t.s, t.p, v.o.value))
                    else:
                        resp = self.tg.get_all(
                            limit=v.limit
                        )
                        for t in resp:
                            triples.append((t.s, t.p, t.o))

            triples = [
                Triple(
                    s=self.create_value(t[0]),
                    p=self.create_value(t[1]), 
                    o=self.create_value(t[2])
                )
                for t in triples
            ]

            print("Send response...", flush=True)
            r = TriplesQueryResponse(triples=triples, error=None)
            await self.send(r, properties={"id": id})

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

            await self.send(r, properties={"id": id})

            self.consumer.acknowledge(msg)

    @staticmethod
    def add_args(parser):

        ConsumerProducer.add_args(
            parser, default_input_queue, default_subscriber,
            default_output_queue,
        )

        parser.add_argument(
            '-g', '--graph-host',
            default="localhost",
            help=f'Graph host (default: localhost)'
        )
        
        parser.add_argument(
            '--graph-username',
            default=None,
            help=f'Cassandra username'
        )
        
        parser.add_argument(
            '--graph-password',
            default=None,
            help=f'Cassandra password'
        )


def run():

    Processor.launch(module, __doc__)

