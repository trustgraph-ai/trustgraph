
import asyncio
import logging

from ... schema import Metadata
from ... schema import Triples

from . serialize import to_subgraph

logger = logging.getLogger(__name__)

class TriplesImport:

    def __init__(self, ws, running, backend, queue):
        self.ws = ws
        self.running = running
        self.backend = backend
        self.queue = queue
        self.producer = None

    async def start(self):
        self.producer = await self.backend.create_producer(
            topic=self.queue, schema=Triples,
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

        elt = Triples(
            metadata=Metadata(
                id=data["metadata"]["id"],
                root=data["metadata"].get("root", ""),
                collection=data["metadata"]["collection"],
            ),
            triples=to_subgraph(data["triples"]),
        )

        await self.producer.send(elt)

    async def run(self):
        while self.running.get():
            await asyncio.sleep(0.5)

        if self.ws:
            await self.ws.close()
        self.ws = None
