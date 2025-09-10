
"""
Triples query service for neo4j.
Input is a (s, p, o) triple, some values may be null.  Output is a list of
triples.
"""

import logging

from neo4j import GraphDatabase

from .... schema import TriplesQueryRequest, TriplesQueryResponse, Error
from .... schema import Value, Triple
from .... base import TriplesQueryService

# Module logger
logger = logging.getLogger(__name__)

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
            return Value(value=ent, is_uri=True)
        else:
            return Value(value=ent, is_uri=False)

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
                            "RETURN $src as src",
                            src=query.s.value, rel=query.p.value, value=query.o.value,
                            user=user, collection=collection,
                            database_=self.db,
                        )

                        for rec in records:
                            triples.append((query.s.value, query.p.value, query.o.value))

                        records, summary, keys = self.io.execute_query(
                            "MATCH (src:Node {uri: $src, user: $user, collection: $collection})-"
                            "[rel:Rel {uri: $rel, user: $user, collection: $collection}]->"
                            "(dest:Node {uri: $uri, user: $user, collection: $collection}) "
                            "RETURN $src as src",
                            src=query.s.value, rel=query.p.value, uri=query.o.value,
                            user=user, collection=collection,
                            database_=self.db,
                        )

                        for rec in records:
                            triples.append((query.s.value, query.p.value, query.o.value))

                    else:

                        # SP

                        records, summary, keys = self.io.execute_query(
                            "MATCH (src:Node {uri: $src, user: $user, collection: $collection})-"
                            "[rel:Rel {uri: $rel, user: $user, collection: $collection}]->"
                            "(dest:Literal {user: $user, collection: $collection}) "
                            "RETURN dest.value as dest",
                            src=query.s.value, rel=query.p.value,
                            user=user, collection=collection,
                            database_=self.db,
                        )

                        for rec in records:
                            data = rec.data()
                            triples.append((query.s.value, query.p.value, data["dest"]))

                        records, summary, keys = self.io.execute_query(
                            "MATCH (src:Node {uri: $src, user: $user, collection: $collection})-"
                            "[rel:Rel {uri: $rel, user: $user, collection: $collection}]->"
                            "(dest:Node {user: $user, collection: $collection}) "
                            "RETURN dest.uri as dest",
                            src=query.s.value, rel=query.p.value,
                            user=user, collection=collection,
                            database_=self.db,
                        )

                        for rec in records:
                            data = rec.data()
                            triples.append((query.s.value, query.p.value, data["dest"]))

                else:

                    if query.o is not None:

                        # SO

                        records, summary, keys = self.io.execute_query(
                            "MATCH (src:Node {uri: $src, user: $user, collection: $collection})-"
                            "[rel:Rel {user: $user, collection: $collection}]->"
                            "(dest:Literal {value: $value, user: $user, collection: $collection}) "
                            "RETURN rel.uri as rel",
                            src=query.s.value, value=query.o.value,
                            user=user, collection=collection,
                            database_=self.db,
                        )

                        for rec in records:
                            data = rec.data()
                            triples.append((query.s.value, data["rel"], query.o.value))

                        records, summary, keys = self.io.execute_query(
                            "MATCH (src:Node {uri: $src, user: $user, collection: $collection})-"
                            "[rel:Rel {user: $user, collection: $collection}]->"
                            "(dest:Node {uri: $uri, user: $user, collection: $collection}) "
                            "RETURN rel.uri as rel",
                            src=query.s.value, uri=query.o.value,
                            user=user, collection=collection,
                            database_=self.db,
                        )

                        for rec in records:
                            data = rec.data()
                            triples.append((query.s.value, data["rel"], query.o.value))

                    else:

                        # S

                        records, summary, keys = self.io.execute_query(
                            "MATCH (src:Node {uri: $src, user: $user, collection: $collection})-"
                            "[rel:Rel {user: $user, collection: $collection}]->"
                            "(dest:Literal {user: $user, collection: $collection}) "
                            "RETURN rel.uri as rel, dest.value as dest",
                            src=query.s.value,
                            user=user, collection=collection,
                            database_=self.db,
                        )

                        for rec in records:
                            data = rec.data()
                            triples.append((query.s.value, data["rel"], data["dest"]))

                        records, summary, keys = self.io.execute_query(
                            "MATCH (src:Node {uri: $src, user: $user, collection: $collection})-"
                            "[rel:Rel {user: $user, collection: $collection}]->"
                            "(dest:Node {user: $user, collection: $collection}) "
                            "RETURN rel.uri as rel, dest.uri as dest",
                            src=query.s.value,
                            user=user, collection=collection,
                            database_=self.db,
                        )

                        for rec in records:
                            data = rec.data()
                            triples.append((query.s.value, data["rel"], data["dest"]))


            else:

                if query.p is not None:

                    if query.o is not None:

                        # PO

                        records, summary, keys = self.io.execute_query(
                            "MATCH (src:Node {user: $user, collection: $collection})-"
                            "[rel:Rel {uri: $uri, user: $user, collection: $collection}]->"
                            "(dest:Literal {value: $value, user: $user, collection: $collection}) "
                            "RETURN src.uri as src",
                            uri=query.p.value, value=query.o.value,
                            user=user, collection=collection,
                            database_=self.db,
                        )

                        for rec in records:
                            data = rec.data()
                            triples.append((data["src"], query.p.value, query.o.value))

                        records, summary, keys = self.io.execute_query(
                            "MATCH (src:Node {user: $user, collection: $collection})-"
                            "[rel:Rel {uri: $uri, user: $user, collection: $collection}]->"
                            "(dest:Node {uri: $dest, user: $user, collection: $collection}) "
                            "RETURN src.uri as src",
                            uri=query.p.value, dest=query.o.value,
                            user=user, collection=collection,
                            database_=self.db,
                        )

                        for rec in records:
                            data = rec.data()
                            triples.append((data["src"], query.p.value, query.o.value))

                    else:

                        # P

                        records, summary, keys = self.io.execute_query(
                            "MATCH (src:Node {user: $user, collection: $collection})-"
                            "[rel:Rel {uri: $uri, user: $user, collection: $collection}]->"
                            "(dest:Literal {user: $user, collection: $collection}) "
                            "RETURN src.uri as src, dest.value as dest",
                            uri=query.p.value,
                            user=user, collection=collection,
                            database_=self.db,
                        )

                        for rec in records:
                            data = rec.data()
                            triples.append((data["src"], query.p.value, data["dest"]))

                        records, summary, keys = self.io.execute_query(
                            "MATCH (src:Node {user: $user, collection: $collection})-"
                            "[rel:Rel {uri: $uri, user: $user, collection: $collection}]->"
                            "(dest:Node {user: $user, collection: $collection}) "
                            "RETURN src.uri as src, dest.uri as dest",
                            uri=query.p.value,
                            user=user, collection=collection,
                            database_=self.db,
                        )

                        for rec in records:
                            data = rec.data()
                            triples.append((data["src"], query.p.value, data["dest"]))

                else:

                    if query.o is not None:

                        # O

                        records, summary, keys = self.io.execute_query(
                            "MATCH (src:Node {user: $user, collection: $collection})-"
                            "[rel:Rel {user: $user, collection: $collection}]->"
                            "(dest:Literal {value: $value, user: $user, collection: $collection}) "
                            "RETURN src.uri as src, rel.uri as rel",
                            value=query.o.value,
                            user=user, collection=collection,
                            database_=self.db,
                        )

                        for rec in records:
                            data = rec.data()
                            triples.append((data["src"], data["rel"], query.o.value))

                        records, summary, keys = self.io.execute_query(
                            "MATCH (src:Node {user: $user, collection: $collection})-"
                            "[rel:Rel {user: $user, collection: $collection}]->"
                            "(dest:Node {uri: $uri, user: $user, collection: $collection}) "
                            "RETURN src.uri as src, rel.uri as rel",
                            uri=query.o.value,
                            user=user, collection=collection,
                            database_=self.db,
                        )

                        for rec in records:
                            data = rec.data()
                            triples.append((data["src"], data["rel"], query.o.value))

                    else:

                        # *

                        records, summary, keys = self.io.execute_query(
                            "MATCH (src:Node {user: $user, collection: $collection})-"
                            "[rel:Rel {user: $user, collection: $collection}]->"
                            "(dest:Literal {user: $user, collection: $collection}) "
                            "RETURN src.uri as src, rel.uri as rel, dest.value as dest",
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
                            "RETURN src.uri as src, rel.uri as rel, dest.uri as dest",
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
                for t in triples
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

