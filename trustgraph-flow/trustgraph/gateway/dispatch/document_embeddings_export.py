
import asyncio
import logging

from ... schema import DocumentEmbeddings

from . serialize import serialize_document_embeddings

logger = logging.getLogger(__name__)

class DocumentEmbeddingsExport:

    def __init__(self, ws, running, backend, queue, consumer, subscriber):
        self.ws = ws
        self.running = running
        self.backend = backend
        self.queue = queue
        self.subscription = subscriber
        self._consumer = None

    async def destroy(self):
        self.running.stop()
        if self._consumer:
            try:
                await self._consumer.close()
            except BaseException:
                pass
            self._consumer = None
        if self.ws and not self.ws.closed:
            await self.ws.close()

    async def receive(self, msg):
        pass

    async def run(self):
        self._consumer = await self.backend.create_consumer(
            topic=self.queue,
            subscription=self.subscription,
            schema=DocumentEmbeddings,
        )

        consecutive_errors = 0
        max_consecutive_errors = 5

        while self.running.get():
            try:
                msg = await asyncio.wait_for(
                    self._consumer.receive(), timeout=0.5,
                )
                await self.ws.send_json(serialize_document_embeddings(msg.value()))
                await self._consumer.acknowledge(msg)
                consecutive_errors = 0

            except asyncio.TimeoutError:
                continue

            except Exception as e:
                logger.error(f"Exception sending to websocket: {e}")
                consecutive_errors += 1
                if consecutive_errors >= max_consecutive_errors:
                    logger.error("Too many consecutive errors, shutting down")
                    break
                await asyncio.sleep(0.1)
