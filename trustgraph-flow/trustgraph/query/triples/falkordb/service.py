
"""
Triples query service for FalkorDB.
Input is a (s, p, o) triple, some values may be null.  Output is a list of
triples.
"""

import logging

from falkordb import FalkorDB

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

default_graph_url = 'falkor://falkordb:6379'
default_database = 'falkordb'

class Processor(TriplesQueryService):

    def __init__(self, **params):

        graph_url = params.get("graph_url", default_graph_url)
        database = params.get("database", default_database)

        super(Processor, self).__init__(
            **params | {
                "graph_url": graph_url,
                "database": database,
            }
        )

        self.db = database

        self.io = FalkorDB.from_url(graph_url).select_graph(database)

    def create_value(self, ent):

        if ent.startswith("http://") or ent.startswith("https://"):
            return Term(type=IRI, iri=ent)
        else:
            return Term(type=LITERAL, value=ent)

    async def query_triples(self, query):

        try:

            triples = []

            if query.s is not None:
                if query.p is not None:
                    if query.o is not None:

                        # SPO

                        records = self.io.query(
                            "MATCH (src:Node {uri: $src})-[rel:Rel {uri: $rel}]->(dest:Literal {value: $value}) "
                            "RETURN $src as src "
                            "LIMIT " + str(query.limit),
                            params={
                                "src": get_term_value(query.s),
                                "rel": get_term_value(query.p),
                                "value": get_term_value(query.o),
                            },
                        ).result_set

                        for rec in records:
                            triples.append((get_term_value(query.s), get_term_value(query.p), get_term_value(query.o)))

                        records = self.io.query(
                            "MATCH (src:Node {uri: $src})-[rel:Rel {uri: $rel}]->(dest:Node {uri: $uri}) "
                            "RETURN $src as src "
                            "LIMIT " + str(query.limit),
                            params={
                                "src": get_term_value(query.s),
                                "rel": get_term_value(query.p),
                                "uri": get_term_value(query.o),
                            },
                        ).result_set

                        for rec in records:
                            triples.append((get_term_value(query.s), get_term_value(query.p), get_term_value(query.o)))

                    else:

                        # SP

                        records = self.io.query(
                            "MATCH (src:Node {uri: $src})-[rel:Rel {uri: $rel}]->(dest:Literal) "
                            "RETURN dest.value as dest "
                            "LIMIT " + str(query.limit),
                            params={
                                "src": get_term_value(query.s),
                                "rel": get_term_value(query.p),
                            },
                        ).result_set

                        for rec in records:
                            triples.append((get_term_value(query.s), get_term_value(query.p), rec[0]))

                        records = self.io.query(
                            "MATCH (src:Node {uri: $src})-[rel:Rel {uri: $rel}]->(dest:Node) "
                            "RETURN dest.uri as dest "
                            "LIMIT " + str(query.limit),
                            params={
                                "src": get_term_value(query.s),
                                "rel": get_term_value(query.p),
                            },
                        ).result_set

                        for rec in records:
                            triples.append((get_term_value(query.s), get_term_value(query.p), rec[0]))

                else:

                    if query.o is not None:

                        # SO

                        records = self.io.query(
                            "MATCH (src:Node {uri: $src})-[rel:Rel]->(dest:Literal {value: $value}) "
                            "RETURN rel.uri as rel "
                            "LIMIT " + str(query.limit),
                            params={
                                "src": get_term_value(query.s),
                                "value": get_term_value(query.o),
                            },
                        ).result_set

                        for rec in records:
                            triples.append((get_term_value(query.s), rec[0], get_term_value(query.o)))

                        records = self.io.query(
                            "MATCH (src:Node {uri: $src})-[rel:Rel]->(dest:Node {uri: $uri}) "
                            "RETURN rel.uri as rel "
                            "LIMIT " + str(query.limit),
                            params={
                                "src": get_term_value(query.s),
                                "uri": get_term_value(query.o),
                            },
                        ).result_set

                        for rec in records:
                            triples.append((get_term_value(query.s), rec[0], get_term_value(query.o)))

                    else:

                        # s

                        records = self.io.query(
                            "MATCH (src:Node {uri: $src})-[rel:Rel]->(dest:Literal) "
                            "RETURN rel.uri as rel, dest.value as dest "
                            "LIMIT " + str(query.limit),
                            params={
                                "src": get_term_value(query.s),
                            },
                        ).result_set

                        for rec in records:
                            triples.append((get_term_value(query.s), rec[0], rec[1]))

                        records = self.io.query(
                            "MATCH (src:Node {uri: $src})-[rel:Rel]->(dest:Node) "
                            "RETURN rel.uri as rel, dest.uri as dest "
                            "LIMIT " + str(query.limit),
                            params={
                                "src": get_term_value(query.s),
                            },
                        ).result_set

                        for rec in records:
                            triples.append((get_term_value(query.s), rec[0], rec[1]))


            else:

                if query.p is not None:

                    if query.o is not None:

                        # PO

                        records = self.io.query(
                            "MATCH (src:Node)-[rel:Rel {uri: $uri}]->(dest:Literal {value: $value}) "
                            "RETURN src.uri as src "
                            "LIMIT " + str(query.limit),
                            params={
                                "uri": get_term_value(query.p),
                                "value": get_term_value(query.o),
                            },
                        ).result_set

                        for rec in records:
                            triples.append((rec[0], get_term_value(query.p), get_term_value(query.o)))

                        records = self.io.query(
                            "MATCH (src:Node)-[rel:Rel {uri: $uri}]->(dest:Node {uri: $dest}) "
                            "RETURN src.uri as src "
                            "LIMIT " + str(query.limit),
                            params={
                                "uri": get_term_value(query.p),
                                "dest": get_term_value(query.o),
                            },
                        ).result_set

                        for rec in records:
                            triples.append((rec[0], get_term_value(query.p), get_term_value(query.o)))

                    else:

                        # P

                        records = self.io.query(
                            "MATCH (src:Node)-[rel:Rel {uri: $uri}]->(dest:Literal) "
                            "RETURN src.uri as src, dest.value as dest "
                            "LIMIT " + str(query.limit),
                            params={
                                "uri": get_term_value(query.p),
                            },
                        ).result_set

                        for rec in records:
                            triples.append((rec[0], get_term_value(query.p), rec[1]))

                        records = self.io.query(
                            "MATCH (src:Node)-[rel:Rel {uri: $uri}]->(dest:Node) "
                            "RETURN src.uri as src, dest.uri as dest "
                            "LIMIT " + str(query.limit),
                            params={
                                "uri": get_term_value(query.p),
                            },
                        ).result_set

                        for rec in records:
                            triples.append((rec[0], get_term_value(query.p), rec[1]))

                else:

                    if query.o is not None:

                        # O

                        records = self.io.query(
                            "MATCH (src:Node)-[rel:Rel]->(dest:Literal {value: $value}) "
                            "RETURN src.uri as src, rel.uri as rel "
                            "LIMIT " + str(query.limit),
                            params={
                                "value": get_term_value(query.o),
                            },
                        ).result_set

                        for rec in records:
                            triples.append((rec[0], rec[1], get_term_value(query.o)))

                        records = self.io.query(
                            "MATCH (src:Node)-[rel:Rel]->(dest:Node {uri: $uri}) "
                            "RETURN src.uri as src, rel.uri as rel "
                            "LIMIT " + str(query.limit),
                            params={
                                "uri": get_term_value(query.o),
                            },
                        ).result_set

                        for rec in records:
                            triples.append((rec[0], rec[1], get_term_value(query.o)))

                    else:

                        # *

                        records = self.io.query(
                            "MATCH (src:Node)-[rel:Rel]->(dest:Literal) "
                            "RETURN src.uri as src, rel.uri as rel, dest.value as dest "
                            "LIMIT " + str(query.limit),
                        ).result_set

                        for rec in records:
                            triples.append((rec[0], rec[1], rec[2]))

                        records = self.io.query(
                            "MATCH (src:Node)-[rel:Rel]->(dest:Node) "
                            "RETURN src.uri as src, rel.uri as rel, dest.uri as dest "
                            "LIMIT " + str(query.limit),
                        ).result_set

                        for rec in records:
                            triples.append((rec[0], rec[1], rec[2]))

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
            '-g', '--graph-url',
            default=default_graph_url,
            help=f'Graph url (default: {default_graph_url})'
        )

        parser.add_argument(
            '--database',
            default=default_database,
            help=f'FalkorDB database (default: {default_database})'
        )

def run():

    Processor.launch(default_ident, __doc__)

