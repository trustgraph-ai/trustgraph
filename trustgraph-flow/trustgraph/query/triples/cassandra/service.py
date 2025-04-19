
"""
Triples query service.  Input is a (s, p, o) triple, some values may be
null.  Output is a list of triples.
"""

from .... direct.cassandra import TrustGraph
from .... schema import TriplesQueryRequest, TriplesQueryResponse, Error
from .... schema import Value, Triple
from .... base import TriplesQueryService

default_ident = "triples-query"

default_graph_host='localhost'

class Processor(TriplesQueryService):

    def __init__(self, **params):

        graph_host = params.get("graph_host", default_graph_host)
        graph_username = params.get("graph_username", None)
        graph_password = params.get("graph_password", None)

        super(Processor, self).__init__(
            **params | {
                "graph_host": graph_host,
                "graph_username": graph_username,
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

    async def query_triples(self, query):

        try:

            table = (query.user, query.collection)

            if table != self.table:
                if self.username and self.password:
                    self.tg = TrustGraph(
                        hosts=self.graph_host,
                        keyspace=query.user, table=query.collection,
                        username=self.username, password=self.password
                    )
                else:
                    self.tg = TrustGraph(
                        hosts=self.graph_host,
                        keyspace=query.user, table=query.collection,
                    )
                self.table = table

            # Sender-produced ID
            id = msg.properties()["id"]

            print(f"Handling input {id}...", flush=True)

            triples = []

            if query.s is not None:
                if query.p is not None:
                    if query.o is not None:
                        resp = self.tg.get_spo(
                            query.s.value, query.p.value, query.o.value,
                            limit=query.limit
                        )
                        triples.append((query.s.value, query.p.value, query.o.value))
                    else:
                        resp = self.tg.get_sp(
                            query.s.value, query.p.value,
                            limit=query.limit
                        )
                        for t in resp:
                            triples.append((query.s.value, query.p.value, t.o))
                else:
                    if query.o is not None:
                        resp = self.tg.get_os(
                            query.o.value, query.s.value, 
                            limit=query.limit
                        )
                        for t in resp:
                            triples.append((query.s.value, t.p, query.o.value))
                    else:
                        resp = self.tg.get_s(
                            query.s.value,
                            limit=query.limit
                        )
                        for t in resp:
                            triples.append((query.s.value, t.p, t.o))
            else:
                if query.p is not None:
                    if query.o is not None:
                        resp = self.tg.get_po(
                            query.p.value, query.o.value,
                            limit=query.limit
                        )
                        for t in resp:
                            triples.append((t.s, query.p.value, query.o.value))
                    else:
                        resp = self.tg.get_p(
                            query.p.value,
                            limit=query.limit
                        )
                        for t in resp:
                            triples.append((t.s, query.p.value, t.o))
                else:
                    if query.o is not None:
                        resp = self.tg.get_o(
                            query.o.value,
                            limit=query.limit
                        )
                        for t in resp:
                            triples.append((t.s, t.p, query.o.value))
                    else:
                        resp = self.tg.get_all(
                            limit=query.limit
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

            return triples

            print("Done.", flush=True)

        except Exception as e:

            print(f"Exception: {e}")
            raise e

    @staticmethod
    def add_args(parser):

        TriplesQueryService.add_args(parser)

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

    Processor.launch(default_ident, __doc__)

