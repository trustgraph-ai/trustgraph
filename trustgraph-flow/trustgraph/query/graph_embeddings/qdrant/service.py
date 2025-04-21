
"""
Graph embeddings query service.  Input is vector, output is list of
entities
"""

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from qdrant_client.models import Distance, VectorParams

from .... schema import GraphEmbeddingsResponse
from .... schema import Error, Value
from .... base import GraphEmbeddingsQueryService

default_ident = "ge-query"

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

    def create_value(self, ent):
        if ent.startswith("http://") or ent.startswith("https://"):
            return Value(value=ent, is_uri=True)
        else:
            return Value(value=ent, is_uri=False)
        
    async def query_graph_embeddings(self, msg):

        try:

            entity_set = set()
            entities = []

            for vec in msg.vectors:

                dim = len(vec)
                collection = (
                    "t_" + msg.user + "_" + msg.collection + "_" +
                    str(dim)
                )

                # Heuristic hack, get (2*limit), so that we have more chance
                # of getting (limit) entities
                search_result = self.qdrant.query_points(
                    collection_name=collection,
                    query=vec,
                    limit=msg.limit * 2,
                    with_payload=True,
                ).points

                for r in search_result:
                    ent = r.payload["entity"]

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

            print("Send response...", flush=True)
            return entities

            print("Done.", flush=True)

        except Exception as e:

            print(f"Exception: {e}")
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

