
"""
Graph embeddings query service.  Input is vector, output is list of
entities
"""

import logging

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from qdrant_client.models import Distance, VectorParams

from .... schema import GraphEmbeddingsResponse, EntityMatch
from .... schema import Error, Term, IRI, LITERAL
from .... base import GraphEmbeddingsQueryService

# Module logger
logger = logging.getLogger(__name__)

default_ident = "graph-embeddings-query"

default_store_uri = 'http://localhost:6333'

class Processor(GraphEmbeddingsQueryService):

    def __init__(self, **params):

        store_uri = params.get("store_uri", default_store_uri)

        #optional api key
        api_key = params.get("api_key", None)

        super(Processor, self).__init__(
            **params | {
                "store_uri": store_uri,
                "api_key": api_key,
            }
        )

        self.qdrant = QdrantClient(url=store_uri, api_key=api_key)
        self.last_collection = None

    def ensure_collection_exists(self, collection, dim):
        """Ensure collection exists, create if it doesn't"""
        if collection != self.last_collection:
            if not self.qdrant.collection_exists(collection):
                try:
                    self.qdrant.create_collection(
                        collection_name=collection,
                        vectors_config=VectorParams(
                            size=dim, distance=Distance.COSINE
                        ),
                    )
                    logger.info(f"Created collection: {collection}")
                except Exception as e:
                    logger.error(f"Qdrant collection creation failed: {e}")
                    raise e
            self.last_collection = collection

    def collection_exists(self, collection):
        """Check if collection exists (no implicit creation)"""
        return self.qdrant.collection_exists(collection)

    def collection_exists(self, collection):
        """Check if collection exists (no implicit creation)"""
        return self.qdrant.collection_exists(collection)

    def create_value(self, ent):
        if ent.startswith("http://") or ent.startswith("https://"):
            return Term(type=IRI, iri=ent)
        else:
            return Term(type=LITERAL, value=ent)
        
    async def query_graph_embeddings(self, workspace, msg):

        try:

            vec = msg.vector
            if not vec:
                return []

            # Use dimension suffix in collection name
            dim = len(vec)
            collection = f"t_{workspace}_{msg.collection}_{dim}"

            # Check if collection exists - return empty if not
            if not self.collection_exists(collection):
                logger.info(f"Collection {collection} does not exist")
                return []

            # Heuristic hack, get (2*limit), so that we have more chance
            # of getting (limit) unique entities
            search_result = self.qdrant.query_points(
                collection_name=collection,
                query=vec,
                limit=msg.limit * 2,
                with_payload=True,
            ).points

            entity_set = set()
            entities = []

            for r in search_result:
                ent = r.payload["entity"]
                score = r.score if hasattr(r, 'score') else 0.0

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
            help=f'Qdrant store URI (default: {default_store_uri})'
        )
        
        parser.add_argument(
            '-k', '--api-key',
            default=None,
            help=f'API key for qdrant (default: None)'
        )

def run():

    Processor.launch(default_ident, __doc__)

