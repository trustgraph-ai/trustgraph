
import asyncio
import uuid
from aiohttp import WSMsgType

from ... schema import Metadata
from ... schema import DocumentEmbeddings, ChunkEmbeddings
from ... base import Publisher
from .... base.messaging.translators.document_loading import DocumentEmbeddingsTranslator

class DocumentEmbeddingsImport:

    def __init__(
            self, ws, running, pulsar_client, queue
    ):

        self.ws = ws
        self.running = running
        self.translator = DocumentEmbeddingsTranslator()
        
        self.publisher = Publisher(
            pulsar_client, topic = queue, schema = DocumentEmbeddings
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
        elt = self.translator.to_pulsar(data)
        await self.publisher.send(None, elt)

    async def run(self):

        while self.running.get():
            await asyncio.sleep(0.5)

        if self.ws:
            await self.ws.close()

        self.ws = None

