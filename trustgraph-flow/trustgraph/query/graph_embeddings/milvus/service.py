
"""
Graph embeddings query service.  Input is vector, output is list of
entities
"""

import logging

from .... direct.milvus_graph_embeddings import EntityVectors
from .... schema import GraphEmbeddingsResponse, EntityMatch
from .... schema import Error, Term, IRI, LITERAL
from .... base import GraphEmbeddingsQueryService

# Module logger
logger = logging.getLogger(__name__)

default_ident = "graph-embeddings-query"
default_store_uri = 'http://localhost:19530'

class Processor(GraphEmbeddingsQueryService):

    def __init__(self, **params):

        store_uri = params.get("store_uri", default_store_uri)

        super(Processor, self).__init__(
            **params | {
                "store_uri": store_uri,
            }
        )

        self.vecstore = EntityVectors(store_uri)

    def create_value(self, ent):
        if ent.startswith("http://") or ent.startswith("https://"):
            return Term(type=IRI, iri=ent)
        else:
            return Term(type=LITERAL, value=ent)
        
    async def query_graph_embeddings(self, msg):

        try:

            vec = msg.vector
            if not vec:
                return []

            # Handle zero limit case
            if msg.limit <= 0:
                return []

            resp = self.vecstore.search(
                vec,
                msg.user,
                msg.collection,
                limit=msg.limit * 2
            )

            entity_set = set()
            entities = []

            for r in resp:
                ent = r["entity"]["entity"]
                # Milvus returns distance, convert to similarity score
                distance = r.get("distance", 0.0)
                score = 1.0 - distance if distance else 0.0

                # De-dupe entities, keep highest score
                if ent not in entity_set:
                    entity_set.add(ent)
                    entities.append(EntityMatch(
                        entity=self.create_value(ent),
                        score=score,
                    ))

                # Keep adding entities until limit
                if len(entities) >= msg.limit:
                    break

            logger.debug("Send response...")
            return entities

        except Exception as e:

            logger.error(f"Exception querying graph embeddings: {e}", exc_info=True)
            raise e

    @staticmethod
    def add_args(parser):

        GraphEmbeddingsQueryService.add_args(parser)

        parser.add_argument(
            '-t', '--store-uri',
            default=default_store_uri,
            help=f'Milvus store URI (default: {default_store_uri})'
        )

def run():

    Processor.launch(default_ident, __doc__)

