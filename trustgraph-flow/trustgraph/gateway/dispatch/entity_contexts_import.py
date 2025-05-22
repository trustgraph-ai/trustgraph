
import asyncio
import uuid
from aiohttp import WSMsgType

from ... schema import Metadata
from ... schema import EntityContexts, EntityContext
from ... base import Publisher

from . serialize import to_subgraph, to_value

class EntityContextsImport:

    def __init__(
            self, ws, running, pulsar_client, queue
    ):

        self.ws = ws
        self.running = running
        
        self.publisher = Publisher(
            pulsar_client, topic = queue, schema = EntityContexts
        )

    async def start(self):
        await self.publisher.start()

    async def destroy(self):
        self.running.stop()

        if self.ws:
            await self.ws.close()

        await self.publisher.stop()

    async def receive(self, msg):

        data = msg.json()

        elt = EntityContexts(
            metadata=Metadata(
                id=data["metadata"]["id"],
                metadata=to_subgraph(data["metadata"]["metadata"]),
                user=data["metadata"]["user"],
                collection=data["metadata"]["collection"],
            ),
            entities=[
                EntityContext(
                    entity=to_value(ent["entity"]),
                    context=ent["context"],
                )
                for ent in data["entities"]
            ]
        )

        await self.publisher.send(None, elt)

    async def run(self):

        while self.running.get():
            await asyncio.sleep(0.5)

        if self.ws:
            await self.ws.close()

        self.ws = None

