
import asyncio
import queue
import uuid

from ... schema import DocumentEmbeddings
from ... schema import document_embeddings_store_queue
from ... base import Subscriber

from . socket import SocketEndpoint
from . serialize import serialize_document_embeddings

class DocumentEmbeddingsStreamEndpoint(SocketEndpoint):

    def __init__(
            self, pulsar_client, auth,
            queue,
            path="/api/v1/stream/document-embeddings",
    ):

        super(DocumentEmbeddingsStreamEndpoint, self).__init__(
            endpoint_path=path, auth=auth,
        )

        self.pulsar_client=pulsar_client

        self.subscriber = Subscriber(
            self.pulsar_client, queue,
            "api-gateway", "api-gateway",
            schema=DocumentEmbeddings,
        )

    async def listener(self, ws, running):

        worker = asyncio.create_task(
            self.async_thread(ws, running)
        )

        await super(DocumentEmbeddingsStreamEndpoint, self).listener(
            ws, running
        )

        await worker

    async def start(self):

        await self.subscriber.start()

    async def async_thread(self, ws, running):

        id = str(uuid.uuid4())

        q = await self.subscriber.subscribe_all(id)

        while running.get():
            try:
                resp = await asyncio.wait_for(q.get(), timeout=0.5)
                await ws.send_json(serialize_document_embeddings(resp))

            except TimeoutError:
                continue

            except queue.Empty:
                continue

            except Exception as e:
                print(f"Exception: {str(e)}", flush=True)
                break

        await self.subscriber.unsubscribe_all(id)

        running.stop()

