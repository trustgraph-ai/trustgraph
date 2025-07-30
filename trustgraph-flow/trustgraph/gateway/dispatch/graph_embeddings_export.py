
import asyncio
import queue
import uuid
import logging

from ... schema import GraphEmbeddings
from ... base import Subscriber

from . serialize import serialize_graph_embeddings

# Module logger
logger = logging.getLogger(__name__)

class GraphEmbeddingsExport:

    def __init__(
            self, ws, running, pulsar_client, queue, consumer, subscriber
    ):

        self.ws = ws
        self.running = running
        self.pulsar_client = pulsar_client
        self.queue = queue
        self.consumer = consumer
        self.subscriber = subscriber

    async def destroy(self):
        self.running.stop()
        await self.ws.close()

    async def receive(self, msg):
        # Ignore incoming info from websocket
        pass

    async def run(self):

        subs = Subscriber(
            client = self.pulsar_client, topic = self.queue,
            consumer_name = self.consumer, subscription = self.subscriber,
            schema = GraphEmbeddings
        )

        await subs.start()

        id = str(uuid.uuid4())
        q = await subs.subscribe_all(id)

        while self.running.get():
            try:

                resp = await asyncio.wait_for(q.get(), timeout=0.5)
                await self.ws.send_json(serialize_graph_embeddings(resp))

            except TimeoutError:
                continue

            except queue.Empty:
                continue

            except Exception as e:
                logger.error(f"Exception: {str(e)}", exc_info=True)
                break

        await subs.unsubscribe_all(id)

        await subs.stop()

        await self.ws.close()
        self.running.stop()

