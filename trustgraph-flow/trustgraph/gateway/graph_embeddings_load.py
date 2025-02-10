
import asyncio
from pulsar.schema import JsonSchema
import uuid
from aiohttp import WSMsgType

from .. schema import Metadata
from .. schema import GraphEmbeddings, EntityEmbeddings
from .. schema import graph_embeddings_store_queue

from . publisher import Publisher
from . socket import SocketEndpoint
from . serialize import to_subgraph, to_value

class GraphEmbeddingsLoadEndpoint(SocketEndpoint):

    def __init__(
            self, pulsar_host, auth, pulsar_api_key=None, path="/api/v1/load/graph-embeddings",
    ):

        super(GraphEmbeddingsLoadEndpoint, self).__init__(
            endpoint_path=path, auth=auth,
        )

        self.pulsar_host=pulsar_host
        self.pulsar_api_key=pulsar_api_key

        self.publisher = Publisher(
            self.pulsar_host, graph_embeddings_store_queue,
            self.pulsar_api_key,
            schema=JsonSchema(GraphEmbeddings)
        )

    async def start(self):

        self.publisher.start()

    async def listener(self, ws, running):
        
        async for msg in ws:
            # On error, finish
            if msg.type == WSMsgType.ERROR:
                break
            else:

                data = msg.json()

                elt = GraphEmbeddings(
                    metadata=Metadata(
                        id=data["metadata"]["id"],
                        metadata=to_subgraph(data["metadata"]["metadata"]),
                        user=data["metadata"]["user"],
                        collection=data["metadata"]["collection"],
                    ),
                    entities=[
                        EntityEmbeddings(
                            entity=to_value(ent["entity"]),
                            vectors=ent["vectors"],
                        )
                        for ent in data["entities"]
                    ]
                )

                self.publisher.send(None, elt)


        running.stop()
