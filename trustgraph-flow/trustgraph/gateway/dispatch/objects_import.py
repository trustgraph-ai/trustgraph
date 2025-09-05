import asyncio
import uuid
import logging
from aiohttp import WSMsgType

from ... schema import Metadata
from ... schema import ExtractedObject
from ... base import Publisher

from . serialize import to_subgraph

# Module logger
logger = logging.getLogger(__name__)

class ObjectsImport:

    def __init__(
            self, ws, running, pulsar_client, queue
    ):

        self.ws = ws
        self.running = running
        
        self.publisher = Publisher(
            pulsar_client, topic = queue, schema = ExtractedObject
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

        elt = ExtractedObject(
            metadata=Metadata(
                id=data["metadata"]["id"],
                metadata=to_subgraph(data["metadata"].get("metadata", [])),
                user=data["metadata"]["user"],
                collection=data["metadata"]["collection"],
            ),
            schema_name=data["schema_name"],
            values=data["values"],
            confidence=data.get("confidence", 1.0),
            source_span=data.get("source_span", ""),
        )

        await self.publisher.send(None, elt)

    async def run(self):

        while self.running.get():
            await asyncio.sleep(0.5)

        if self.ws:
            await self.ws.close()

        self.ws = None