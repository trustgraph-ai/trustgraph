
import asyncio
import logging

from ... schema import Metadata
from ... schema import EntityContexts, EntityContext

from . serialize import to_value

logger = logging.getLogger(__name__)

class EntityContextsImport:

    def __init__(self, ws, running, backend, queue):
        self.ws = ws
        self.running = running
        self.backend = backend
        self.queue = queue
        self.producer = None

    async def start(self):
        self.producer = await self.backend.create_producer(
            topic=self.queue, schema=EntityContexts,
        )

    async def destroy(self):
        self.running.stop()
        if self.producer:
            await self.producer.close()
            self.producer = None
        if self.ws:
            await self.ws.close()

    async def receive(self, msg):
        data = msg.json()

        elt = EntityContexts(
            metadata=Metadata(
                id=data["metadata"]["id"],
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

        await self.producer.send(elt)

    async def run(self):
        while self.running.get():
            await asyncio.sleep(0.5)

        if self.ws:
            await self.ws.close()
        self.ws = None
