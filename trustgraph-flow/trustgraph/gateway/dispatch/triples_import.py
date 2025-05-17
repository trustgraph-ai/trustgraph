
import asyncio
import uuid
from aiohttp import WSMsgType

from ... schema import Metadata
from ... schema import Triples
from ... base import Publisher

from . serialize import to_subgraph

class TriplesImport:

    def __init__(
            self, ws, running, pulsar_client, queue
    ):

        self.ws = ws
        self.running = running
        
        self.publisher = Publisher(
            pulsar_client, topic = queue, schema = Triples
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

