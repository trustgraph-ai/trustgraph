
"""
Graph embeddings query service.  Input is vector, output is list of
entities
"""

import logging

from .... direct.milvus_graph_embeddings import EntityVectors
from .... schema import GraphEmbeddingsResponse
from .... schema import Error, Value
from .... base import GraphEmbeddingsQueryService

# Module logger
logger = logging.getLogger(__name__)

default_ident = "ge-query"
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
            return Value(value=ent, is_uri=True)
        else:
            return Value(value=ent, is_uri=False)
        
    async def query_graph_embeddings(self, msg):

        try:

            entity_set = set()
            entities = []

            # Handle zero limit case
            if msg.limit <= 0:
                return []

            for vec in msg.vectors:

                resp = self.vecstore.search(
                    vec, 
                    msg.user, 
                    msg.collection, 
                    limit=msg.limit * 2
                )

                for r in resp:
                    ent = r["entity"]["entity"]
                    
                    # De-dupe entities
                    if ent not in entity_set:
                        entity_set.add(ent)
                        entities.append(ent)

                    # Keep adding entities until limit
                    if len(entity_set) >= msg.limit: break

                # Keep adding entities until limit
                if len(entity_set) >= msg.limit: break

            ents2 = []

            for ent in entities:
                ents2.append(self.create_value(ent))

            entities = ents2

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

