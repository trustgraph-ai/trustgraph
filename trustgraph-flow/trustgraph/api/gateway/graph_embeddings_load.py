
import asyncio
from pulsar.schema import JsonSchema
import uuid
from aiohttp import WSMsgType

from ... schema import Metadata
from ... schema import GraphEmbeddings
from ... schema import graph_embeddings_store_queue

from . publisher import Publisher
from . socket import SocketEndpoint
from . serialize import to_subgraph, to_value

class GraphEmbeddingsLoadEndpoint(SocketEndpoint):

    def __init__(self, pulsar_host, path="/api/v1/load/graph-embeddings"):

        super(GraphEmbeddingsLoadEndpoint, self).__init__(
            endpoint_path=path
        )

        self.pulsar_host=pulsar_host

        self.publisher = Publisher(
            self.pulsar_host, graph_embeddings_store_queue,
            schema=JsonSchema(GraphEmbeddings)
        )

    async def start(self):

        self.task = asyncio.create_task(
            self.publisher.run()
        )

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
                    entity=to_value(data["entity"]),
                    vectors=data["vectors"],
                )

                await self.publisher.send(None, elt)


        running.stop()
