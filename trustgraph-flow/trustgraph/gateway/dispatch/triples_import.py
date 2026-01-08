
import asyncio
import uuid
import logging
from aiohttp import WSMsgType

from ... schema import Metadata
from ... schema import Triples
from ... base import Publisher

from . serialize import to_subgraph

# Module logger
logger = logging.getLogger(__name__)

class TriplesImport:

    def __init__(
            self, ws, running, backend, queue
    ):

        self.ws = ws
        self.running = running
        
        self.publisher = Publisher(
            backend, topic = queue, schema = Triples
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

        elt = Triples(
            metadata=Metadata(
                id=data["metadata"]["id"],
                metadata=to_subgraph(data["metadata"]["metadata"]),
                user=data["metadata"]["user"],
                collection=data["metadata"]["collection"],
            ),
            triples=to_subgraph(data["triples"]),
        )

        await self.publisher.send(None, elt)

    async def run(self):

        while self.running.get():
            await asyncio.sleep(0.5)

        if self.ws:
            await self.ws.close()

        self.ws = None

