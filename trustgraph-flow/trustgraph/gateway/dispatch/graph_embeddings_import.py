
import asyncio
import uuid
from aiohttp import WSMsgType

from ... schema import Metadata
from ... schema import GraphEmbeddings, EntityEmbeddings
from ... base import Publisher

from . serialize import to_subgraph, to_value

class GraphEmbeddingsImport:

    def __init__(
            self, ws, running, pulsar_client, queue
    ):

        self.ws = ws
        self.running = running
        
        self.publisher = Publisher(
            pulsar_client, topic = queue, schema = GraphEmbeddings
        )

    async def destroy(self):
        self.running.stop()
        await self.ws.close()
        await self.publisher.stop()

    async def receive(self, msg):

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

    async def run(self):

        while self.running.get():
            await asyncio.sleep(0.5)

        await self.ws.close()
        self.ws = None

