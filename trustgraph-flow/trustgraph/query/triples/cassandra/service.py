
"""
Triples query service.  Input is a (s, p, o) triple, some values may be
null.  Output is a list of triples.
"""

import logging

from .... direct.cassandra_kg import KnowledgeGraph
from .... schema import TriplesQueryRequest, TriplesQueryResponse, Error
from .... schema import Value, Triple
from .... base import TriplesQueryService
from .... base.cassandra_config import add_cassandra_args, resolve_cassandra_config

# Module logger
logger = logging.getLogger(__name__)

default_ident = "triples-query"


class Processor(TriplesQueryService):

    def __init__(self, **params):

        # Get Cassandra parameters
        cassandra_host = params.get("cassandra_host")
        cassandra_username = params.get("cassandra_username")
        cassandra_password = params.get("cassandra_password")

        # Resolve configuration with environment variable fallback
        hosts, username, password = resolve_cassandra_config(
            host=cassandra_host,
            username=cassandra_username,
            password=cassandra_password
        )

        super(Processor, self).__init__(
            **params | {
                "cassandra_host": ','.join(hosts),
                "cassandra_username": username,
            }
        )

        self.cassandra_host = hosts
        self.cassandra_username = username
        self.cassandra_password = password
        self.table = None

    def create_value(self, ent):
        if ent.startswith("http://") or ent.startswith("https://"):
            return Value(value=ent, is_uri=True)
        else:
            return Value(value=ent, is_uri=False)

    async def query_triples(self, query):

        try:

            user = query.user

            if user != self.table:
                if self.cassandra_username and self.cassandra_password:
                    self.tg = KnowledgeGraph(
                        hosts=self.cassandra_host,
                        keyspace=query.user,
                        username=self.cassandra_username, password=self.cassandra_password
                    )
                else:
                    self.tg = KnowledgeGraph(
                        hosts=self.cassandra_host,
                        keyspace=query.user,
                    )
                self.table = user

            triples = []

            if query.s is not None:
                if query.p is not None:
                    if query.o is not None:
                        resp = self.tg.get_spo(
                            query.collection, query.s.value, query.p.value, query.o.value,
                            limit=query.limit
                        )
                        triples.append((query.s.value, query.p.value, query.o.value))
                    else:
                        resp = self.tg.get_sp(
                            query.collection, query.s.value, query.p.value,
                            limit=query.limit
                        )
                        for t in resp:
                            triples.append((query.s.value, query.p.value, t.o))
                else:
                    if query.o is not None:
                        resp = self.tg.get_os(
                            query.collection, query.o.value, query.s.value,
                            limit=query.limit
                        )
                        for t in resp:
                            triples.append((query.s.value, t.p, query.o.value))
                    else:
                        resp = self.tg.get_s(
                            query.collection, query.s.value,
                            limit=query.limit
                        )
                        for t in resp:
                            triples.append((query.s.value, t.p, t.o))
            else:
                if query.p is not None:
                    if query.o is not None:
                        resp = self.tg.get_po(
                            query.collection, query.p.value, query.o.value,
                            limit=query.limit
                        )
                        for t in resp:
                            triples.append((t.s, query.p.value, query.o.value))
                    else:
                        resp = self.tg.get_p(
                            query.collection, query.p.value,
                            limit=query.limit
                        )
                        for t in resp:
                            triples.append((t.s, query.p.value, t.o))
                else:
                    if query.o is not None:
                        resp = self.tg.get_o(
                            query.collection, query.o.value,
                            limit=query.limit
                        )
                        for t in resp:
                            triples.append((t.s, t.p, query.o.value))
                    else:
                        resp = self.tg.get_all(
                            query.collection,
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

        except Exception as e:

            logger.error(f"Exception querying triples: {e}", exc_info=True)
            raise e

    @staticmethod
    def add_args(parser):

        TriplesQueryService.add_args(parser)
        add_cassandra_args(parser)


def run():

    Processor.launch(default_ident, __doc__)

