
"""
Triples query service.  Input is a (s, p, o, g) quad pattern, some values may be
null.  Output is a list of quads.
"""

import logging

from .... direct.cassandra_kg import KnowledgeGraph, GRAPH_WILDCARD, DEFAULT_GRAPH
from .... schema import TriplesQueryRequest, TriplesQueryResponse, Error
from .... schema import Term, Triple, IRI, LITERAL
from .... base import TriplesQueryService
from .... base.cassandra_config import add_cassandra_args, resolve_cassandra_config

# Module logger
logger = logging.getLogger(__name__)

default_ident = "triples-query"


def get_term_value(term):
    """Extract the string value from a Term"""
    if term is None:
        return None
    if term.type == IRI:
        return term.iri
    elif term.type == LITERAL:
        return term.value
    else:
        # For blank nodes or other types, use id or value
        return term.id or term.value


def create_term(value):
    """Create a Term from a string value"""
    if value.startswith("http://") or value.startswith("https://"):
        return Term(type=IRI, iri=value)
    else:
        return Term(type=LITERAL, value=value)


class Processor(TriplesQueryService):

    def __init__(self, **params):

        # Get Cassandra parameters
        cassandra_host = params.get("cassandra_host")
        cassandra_username = params.get("cassandra_username")
        cassandra_password = params.get("cassandra_password")

        # Resolve configuration with environment variable fallback
        hosts, username, password, keyspace = resolve_cassandra_config(
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

            # Extract values from query
            s_val = get_term_value(query.s)
            p_val = get_term_value(query.p)
            o_val = get_term_value(query.o)
            g_val = query.g  # Already a string or None

            quads = []

            # Route to appropriate query method based on which fields are specified
            if s_val is not None:
                if p_val is not None:
                    if o_val is not None:
                        # SPO specified - find matching graphs
                        resp = self.tg.get_spo(
                            query.collection, s_val, p_val, o_val, g=g_val,
                            limit=query.limit
                        )
                        for t in resp:
                            g = t.g if hasattr(t, 'g') else DEFAULT_GRAPH
                            quads.append((s_val, p_val, o_val, g))
                    else:
                        # SP specified
                        resp = self.tg.get_sp(
                            query.collection, s_val, p_val, g=g_val,
                            limit=query.limit
                        )
                        for t in resp:
                            g = t.g if hasattr(t, 'g') else DEFAULT_GRAPH
                            quads.append((s_val, p_val, t.o, g))
                else:
                    if o_val is not None:
                        # SO specified
                        resp = self.tg.get_os(
                            query.collection, o_val, s_val, g=g_val,
                            limit=query.limit
                        )
                        for t in resp:
                            g = t.g if hasattr(t, 'g') else DEFAULT_GRAPH
                            quads.append((s_val, t.p, o_val, g))
                    else:
                        # S only
                        resp = self.tg.get_s(
                            query.collection, s_val, g=g_val,
                            limit=query.limit
                        )
                        for t in resp:
                            g = t.g if hasattr(t, 'g') else DEFAULT_GRAPH
                            quads.append((s_val, t.p, t.o, g))
            else:
                if p_val is not None:
                    if o_val is not None:
                        # PO specified
                        resp = self.tg.get_po(
                            query.collection, p_val, o_val, g=g_val,
                            limit=query.limit
                        )
                        for t in resp:
                            g = t.g if hasattr(t, 'g') else DEFAULT_GRAPH
                            quads.append((t.s, p_val, o_val, g))
                    else:
                        # P only
                        resp = self.tg.get_p(
                            query.collection, p_val, g=g_val,
                            limit=query.limit
                        )
                        for t in resp:
                            g = t.g if hasattr(t, 'g') else DEFAULT_GRAPH
                            quads.append((t.s, p_val, t.o, g))
                else:
                    if o_val is not None:
                        # O only
                        resp = self.tg.get_o(
                            query.collection, o_val, g=g_val,
                            limit=query.limit
                        )
                        for t in resp:
                            g = t.g if hasattr(t, 'g') else DEFAULT_GRAPH
                            quads.append((t.s, t.p, o_val, g))
                    else:
                        # Nothing specified - get all
                        resp = self.tg.get_all(
                            query.collection,
                            limit=query.limit
                        )
                        for t in resp:
                            g = t.g if hasattr(t, 'g') else DEFAULT_GRAPH
                            quads.append((t.s, t.p, t.o, g))

            # Convert to Triple objects (with g field)
            triples = [
                Triple(
                    s=create_term(q[0]),
                    p=create_term(q[1]),
                    o=create_term(q[2]),
                    g=q[3] if q[3] != DEFAULT_GRAPH else None
                )
                for q in quads
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
