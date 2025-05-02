
import asyncio
import uuid
from aiohttp import WSMsgType

from .. schema import Metadata
from .. schema import DocumentEmbeddings, ChunkEmbeddings
from .. base import Publisher

from . socket import SocketEndpoint
from . serialize import to_subgraph

class DocumentEmbeddingsImport:

    def __init__(
            self, ws, running, pulsar_client, queue
    ):

        self.ws = ws
        self.running = running
        
        self.publisher = Publisher(
            pulsar_client, queue = queue, schema = DocumentEmbeddings
        )

    async def destroy(self):
        self.running.stop()
        await self.ws.close()
        await self.publisher.stop()

    async def receive(self, msg):

        data = msg.json()

        elt = DocumentEmbeddings(
            metadata=Metadata(
                id=data["metadata"]["id"],
                metadata=to_subgraph(data["metadata"]["metadata"]),
                user=data["metadata"]["user"],
                collection=data["metadata"]["collection"],
            ),
            chunks=[
                ChunkEmbeddings(
                    chunk=de["chunk"].encode("utf-8"),
                    vectors=de["vectors"],
                )
                for de in data["chunks"]
            ],
        )

        await self.publisher.send(None, elt)

    async def run(self):

        while self.running.get():
            await asyncio.sleep(0.5)

        await self.ws.close()
        self.ws = None

