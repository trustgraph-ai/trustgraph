
import asyncio
import uuid
from aiohttp import WSMsgType

from .. schema import Metadata
from .. schema import GraphEmbeddings, EntityEmbeddings
from .. schema import graph_embeddings_store_queue
from .. base import Publisher

from . socket import SocketEndpoint
from . serialize import to_subgraph, to_value

class GraphEmbeddingsLoadEndpoint(SocketEndpoint):

    def __init__(
            self, pulsar_client, auth, path="/api/v1/load/graph-embeddings",
    ):

        super(GraphEmbeddingsLoadEndpoint, self).__init__(
            endpoint_path=path, auth=auth,
        )

        self.pulsar_client=pulsar_client

        self.publisher = Publisher(
            self.pulsar_client, graph_embeddings_store_queue,
            schema=GraphEmbeddings
        )

    async def start(self):

        await self.publisher.start()

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

                await self.publisher.send(None, elt)

        running.stop()
