
"""
Triples query service for neo4j.
Input is a (s, p, o) triple, some values may be null.  Output is a list of
triples.
"""

import logging

from neo4j import GraphDatabase

from .... schema import TriplesQueryRequest, TriplesQueryResponse, Error
from .... schema import Term, Triple, IRI, LITERAL
from .... base import TriplesQueryService

# Module logger
logger = logging.getLogger(__name__)


def get_term_value(term):
    """Extract the string value from a Term"""
    if term is None:
        return None
    if term.type == IRI:
        return term.iri
    elif term.type == LITERAL:
        return term.value
    else:
        return term.id or term.value

default_ident = "triples-query"

default_graph_host = 'bolt://neo4j:7687'
default_username = 'neo4j'
default_password = 'password'
default_database = 'neo4j'

class Processor(TriplesQueryService):

    def __init__(self, **params):

        graph_host = params.get("graph_host", default_graph_host)
        username = params.get("username", default_username)
        password = params.get("password", default_password)
        database = params.get("database", default_database)

        super(Processor, self).__init__(
            **params | {
                "graph_host": graph_host,
                "username": username,
                "database": database,
            }
        )

        self.db = database

        self.io = GraphDatabase.driver(graph_host, auth=(username, password))

    def create_value(self, ent):

        if ent.startswith("http://") or ent.startswith("https://"):
            return Term(type=IRI, iri=ent)
        else:
            return Term(type=LITERAL, value=ent)

    async def query_triples(self, query):

        try:

            # Extract user and collection, use defaults if not provided
            user = query.user if query.user else "default"
            collection = query.collection if query.collection else "default"
            
            triples = []

            if query.s is not None:
                if query.p is not None:
                    if query.o is not None:

                        # SPO

                        records, summary, keys = self.io.execute_query(
                            "MATCH (src:Node {uri: $src, user: $user, collection: $collection})-"
                            "[rel:Rel {uri: $rel, user: $user, collection: $collection}]->"
                            "(dest:Literal {value: $value, user: $user, collection: $collection}) "
                            "RETURN $src as src "
                            "LIMIT " + str(query.limit),
                            src=get_term_value(query.s), rel=get_term_value(query.p), value=get_term_value(query.o),
                            user=user, collection=collection,
                            database_=self.db,
                        )

                        for rec in records:
                            triples.append((get_term_value(query.s), get_term_value(query.p), get_term_value(query.o)))

                        records, summary, keys = self.io.execute_query(
                            "MATCH (src:Node {uri: $src, user: $user, collection: $collection})-"
                            "[rel:Rel {uri: $rel, user: $user, collection: $collection}]->"
                            "(dest:Node {uri: $uri, user: $user, collection: $collection}) "
                            "RETURN $src as src "
                            "LIMIT " + str(query.limit),
                            src=get_term_value(query.s), rel=get_term_value(query.p), uri=get_term_value(query.o),
                            user=user, collection=collection,
                            database_=self.db,
                        )

                        for rec in records:
                            triples.append((get_term_value(query.s), get_term_value(query.p), get_term_value(query.o)))

                    else:

                        # SP

                        records, summary, keys = self.io.execute_query(
                            "MATCH (src:Node {uri: $src, user: $user, collection: $collection})-"
                            "[rel:Rel {uri: $rel, user: $user, collection: $collection}]->"
                            "(dest:Literal {user: $user, collection: $collection}) "
                            "RETURN dest.value as dest "
                            "LIMIT " + str(query.limit),
                            src=get_term_value(query.s), rel=get_term_value(query.p),
                            user=user, collection=collection,
                            database_=self.db,
                        )

                        for rec in records:
                            data = rec.data()
                            triples.append((get_term_value(query.s), get_term_value(query.p), data["dest"]))

                        records, summary, keys = self.io.execute_query(
                            "MATCH (src:Node {uri: $src, user: $user, collection: $collection})-"
                            "[rel:Rel {uri: $rel, user: $user, collection: $collection}]->"
                            "(dest:Node {user: $user, collection: $collection}) "
                            "RETURN dest.uri as dest "
                            "LIMIT " + str(query.limit),
                            src=get_term_value(query.s), rel=get_term_value(query.p),
                            user=user, collection=collection,
                            database_=self.db,
                        )

                        for rec in records:
                            data = rec.data()
                            triples.append((get_term_value(query.s), get_term_value(query.p), data["dest"]))

                else:

                    if query.o is not None:

                        # SO

                        records, summary, keys = self.io.execute_query(
                            "MATCH (src:Node {uri: $src, user: $user, collection: $collection})-"
                            "[rel:Rel {user: $user, collection: $collection}]->"
                            "(dest:Literal {value: $value, user: $user, collection: $collection}) "
                            "RETURN rel.uri as rel "
                            "LIMIT " + str(query.limit),
                            src=get_term_value(query.s), value=get_term_value(query.o),
                            user=user, collection=collection,
                            database_=self.db,
                        )

                        for rec in records:
                            data = rec.data()
                            triples.append((get_term_value(query.s), data["rel"], get_term_value(query.o)))

                        records, summary, keys = self.io.execute_query(
                            "MATCH (src:Node {uri: $src, user: $user, collection: $collection})-"
                            "[rel:Rel {user: $user, collection: $collection}]->"
                            "(dest:Node {uri: $uri, user: $user, collection: $collection}) "
                            "RETURN rel.uri as rel "
                            "LIMIT " + str(query.limit),
                            src=get_term_value(query.s), uri=get_term_value(query.o),
                            user=user, collection=collection,
                            database_=self.db,
                        )

                        for rec in records:
                            data = rec.data()
                            triples.append((get_term_value(query.s), data["rel"], get_term_value(query.o)))

                    else:

                        # S

                        records, summary, keys = self.io.execute_query(
                            "MATCH (src:Node {uri: $src, user: $user, collection: $collection})-"
                            "[rel:Rel {user: $user, collection: $collection}]->"
                            "(dest:Literal {user: $user, collection: $collection}) "
                            "RETURN rel.uri as rel, dest.value as dest "
                            "LIMIT " + str(query.limit),
                            src=get_term_value(query.s),
                            user=user, collection=collection,
                            database_=self.db,
                        )

                        for rec in records:
                            data = rec.data()
                            triples.append((get_term_value(query.s), data["rel"], data["dest"]))

                        records, summary, keys = self.io.execute_query(
                            "MATCH (src:Node {uri: $src, user: $user, collection: $collection})-"
                            "[rel:Rel {user: $user, collection: $collection}]->"
                            "(dest:Node {user: $user, collection: $collection}) "
                            "RETURN rel.uri as rel, dest.uri as dest "
                            "LIMIT " + str(query.limit),
                            src=get_term_value(query.s),
                            user=user, collection=collection,
                            database_=self.db,
                        )

                        for rec in records:
                            data = rec.data()
                            triples.append((get_term_value(query.s), data["rel"], data["dest"]))


            else:

                if query.p is not None:

                    if query.o is not None:

                        # PO

                        records, summary, keys = self.io.execute_query(
                            "MATCH (src:Node {user: $user, collection: $collection})-"
                            "[rel:Rel {uri: $uri, user: $user, collection: $collection}]->"
                            "(dest:Literal {value: $value, user: $user, collection: $collection}) "
                            "RETURN src.uri as src "
                            "LIMIT " + str(query.limit),
                            uri=get_term_value(query.p), value=get_term_value(query.o),
                            user=user, collection=collection,
                            database_=self.db,
                        )

                        for rec in records:
                            data = rec.data()
                            triples.append((data["src"], get_term_value(query.p), get_term_value(query.o)))

                        records, summary, keys = self.io.execute_query(
                            "MATCH (src:Node {user: $user, collection: $collection})-"
                            "[rel:Rel {uri: $uri, user: $user, collection: $collection}]->"
                            "(dest:Node {uri: $dest, user: $user, collection: $collection}) "
                            "RETURN src.uri as src "
                            "LIMIT " + str(query.limit),
                            uri=get_term_value(query.p), dest=get_term_value(query.o),
                            user=user, collection=collection,
                            database_=self.db,
                        )

                        for rec in records:
                            data = rec.data()
                            triples.append((data["src"], get_term_value(query.p), get_term_value(query.o)))

                    else:

                        # P

                        records, summary, keys = self.io.execute_query(
                            "MATCH (src:Node {user: $user, collection: $collection})-"
                            "[rel:Rel {uri: $uri, user: $user, collection: $collection}]->"
                            "(dest:Literal {user: $user, collection: $collection}) "
                            "RETURN src.uri as src, dest.value as dest "
                            "LIMIT " + str(query.limit),
                            uri=get_term_value(query.p),
                            user=user, collection=collection,
                            database_=self.db,
                        )

                        for rec in records:
                            data = rec.data()
                            triples.append((data["src"], get_term_value(query.p), data["dest"]))

                        records, summary, keys = self.io.execute_query(
                            "MATCH (src:Node {user: $user, collection: $collection})-"
                            "[rel:Rel {uri: $uri, user: $user, collection: $collection}]->"
                            "(dest:Node {user: $user, collection: $collection}) "
                            "RETURN src.uri as src, dest.uri as dest "
                            "LIMIT " + str(query.limit),
                            uri=get_term_value(query.p),
                            user=user, collection=collection,
                            database_=self.db,
                        )

                        for rec in records:
                            data = rec.data()
                            triples.append((data["src"], get_term_value(query.p), data["dest"]))

                else:

                    if query.o is not None:

                        # O

                        records, summary, keys = self.io.execute_query(
                            "MATCH (src:Node {user: $user, collection: $collection})-"
                            "[rel:Rel {user: $user, collection: $collection}]->"
                            "(dest:Literal {value: $value, user: $user, collection: $collection}) "
                            "RETURN src.uri as src, rel.uri as rel "
                            "LIMIT " + str(query.limit),
                            value=get_term_value(query.o),
                            user=user, collection=collection,
                            database_=self.db,
                        )

                        for rec in records:
                            data = rec.data()
                            triples.append((data["src"], data["rel"], get_term_value(query.o)))

                        records, summary, keys = self.io.execute_query(
                            "MATCH (src:Node {user: $user, collection: $collection})-"
                            "[rel:Rel {user: $user, collection: $collection}]->"
                            "(dest:Node {uri: $uri, user: $user, collection: $collection}) "
                            "RETURN src.uri as src, rel.uri as rel "
                            "LIMIT " + str(query.limit),
                            uri=get_term_value(query.o),
                            user=user, collection=collection,
                            database_=self.db,
                        )

                        for rec in records:
                            data = rec.data()
                            triples.append((data["src"], data["rel"], get_term_value(query.o)))

                    else:

                        # *

                        records, summary, keys = self.io.execute_query(
                            "MATCH (src:Node {user: $user, collection: $collection})-"
                            "[rel:Rel {user: $user, collection: $collection}]->"
                            "(dest:Literal {user: $user, collection: $collection}) "
                            "RETURN src.uri as src, rel.uri as rel, dest.value as dest "
                            "LIMIT " + str(query.limit),
                            user=user, collection=collection,
                            database_=self.db,
                        )

                        for rec in records:
                            data = rec.data()
                            triples.append((data["src"], data["rel"], data["dest"]))

                        records, summary, keys = self.io.execute_query(
                            "MATCH (src:Node {user: $user, collection: $collection})-"
                            "[rel:Rel {user: $user, collection: $collection}]->"
                            "(dest:Node {user: $user, collection: $collection}) "
                            "RETURN src.uri as src, rel.uri as rel, dest.uri as dest "
                            "LIMIT " + str(query.limit),
                            user=user, collection=collection,
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
                for t in triples[:query.limit]
            ]

            return triples

        except Exception as e:

            logger.error(f"Exception querying triples: {e}", exc_info=True)
            raise e
            
    @staticmethod
    def add_args(parser):

        TriplesQueryService.add_args(parser)

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

        parser.add_argument(
            '--database',
            default=default_database,
            help=f'Neo4j database (default: {default_database})'
        )

def run():

    Processor.launch(default_ident, __doc__)

