
import asyncio
import uuid
import logging
from aiohttp import WSMsgType

from ... schema import Metadata
from ... schema import EntityContexts, EntityContext
from ... base import Publisher

from . serialize import to_subgraph, to_value

# Module logger
logger = logging.getLogger(__name__)

class EntityContextsImport:

    def __init__(
            self, ws, running, backend, queue
    ):

        self.ws = ws
        self.running = running
        
        self.publisher = Publisher(
            backend, topic = queue, schema = EntityContexts
        )

    async def start(self):
        await self.publisher.start()

    async def destroy(self):
        # Step 1: Stop accepting new messages
        self.running.stop()

        # Step 2: Wait for publisher to drain its queue
        logger.info("Draining publisher queue...")
        await self.publisher.stop()

        # Step 3: Close websocket only after queue is drained
        if self.ws:
            await self.ws.close()

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

