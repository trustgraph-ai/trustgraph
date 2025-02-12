
import asyncio
import queue
from pulsar.schema import JsonSchema
import uuid

from .. schema import GraphEmbeddings
from .. schema import graph_embeddings_store_queue
from .. base import Subscriber

from . socket import SocketEndpoint
from . serialize import serialize_graph_embeddings

class GraphEmbeddingsStreamEndpoint(SocketEndpoint):

    def __init__(
            self, pulsar_host, auth, path="/api/v1/stream/graph-embeddings", pulsar_api_key=None
    ):

        super(GraphEmbeddingsStreamEndpoint, self).__init__(
            endpoint_path=path, auth=auth,
        )

        self.pulsar_host=pulsar_host
        self.pulsar_api_key=pulsar_api_key

        self.subscriber = Subscriber(
            self.pulsar_host, graph_embeddings_store_queue,
            "api-gateway", "api-gateway",
            pulsar_api_key=self.pulsar_api_key,
            schema=JsonSchema(GraphEmbeddings)
        )

    async def listener(self, ws, running):

        worker = asyncio.create_task(
            self.async_thread(ws, running)
        )

        await super(GraphEmbeddingsStreamEndpoint, self).listener(ws, running)

        await worker

    async def start(self):

        self.subscriber.start()

    async def async_thread(self, ws, running):

        id = str(uuid.uuid4())

        q = self.subscriber.subscribe_all(id)

        while running.get():
            try:
                resp = await asyncio.to_thread(q.get, timeout=0.5)
                await ws.send_json(serialize_graph_embeddings(resp))

            except TimeoutError:
                continue

            except queue.Empty:
                continue

            except Exception as e:
                print(f"Exception: {str(e)}", flush=True)
                break

        self.subscriber.unsubscribe_all(id)

        running.stop()

