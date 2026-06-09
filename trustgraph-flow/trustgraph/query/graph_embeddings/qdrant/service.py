
"""
Graph embeddings query service.  Input is vector, output is list of
entities
"""

import asyncio
import logging

from qdrant_client import QdrantClient

from .... schema import GraphEmbeddingsResponse, EntityMatch
from .... schema import Error, Term, IRI, LITERAL
from .... base import GraphEmbeddingsQueryService
from .... base.qdrant_config import add_qdrant_args, resolve_qdrant_config

# Module logger
logger = logging.getLogger(__name__)

default_ident = "graph-embeddings-query"

class Processor(GraphEmbeddingsQueryService):

    def __init__(self, **params):

        store_uri = params.get("store_uri")
        api_key = params.get("api_key")

        url, api_key, _, _ = resolve_qdrant_config(
            url=store_uri, api_key=api_key,
        )

        super(Processor, self).__init__(
            **params | {
                "store_uri": url,
                "api_key": api_key,
            }
        )

        self.qdrant = QdrantClient(url=url, api_key=api_key)

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

            dim = len(vec)
            collection = f"t_{workspace}_{msg.collection}_{dim}"

            exists = await asyncio.to_thread(
                self.qdrant.collection_exists, collection
            )
            if not exists:
                logger.info(f"Collection {collection} does not exist")
                return []

            # Heuristic hack, get (2*limit), so that we have more chance
            # of getting (limit) unique entities
            result = await asyncio.to_thread(
                self.qdrant.query_points,
                collection_name=collection,
                query=vec,
                limit=msg.limit * 2,
                with_payload=True,
            )
            search_result = result.points

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
        add_qdrant_args(parser)

def run():

    Processor.launch(default_ident, __doc__)

