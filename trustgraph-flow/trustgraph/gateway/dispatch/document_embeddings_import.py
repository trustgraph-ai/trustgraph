
import asyncio
import uuid
import logging
from aiohttp import WSMsgType

from ... schema import Metadata
from ... schema import DocumentEmbeddings, ChunkEmbeddings
from ... base import Publisher
from ... messaging.translators.document_loading import DocumentEmbeddingsTranslator

# Module logger
logger = logging.getLogger(__name__)

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
        elt = self.translator.to_pulsar(data)
        await self.publisher.send(None, elt)

    async def run(self):

        while self.running.get():
            await asyncio.sleep(0.5)

        if self.ws:
            await self.ws.close()

        self.ws = None

