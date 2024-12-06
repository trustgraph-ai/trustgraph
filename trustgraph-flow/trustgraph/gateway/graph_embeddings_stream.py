
import asyncio
import queue
from pulsar.schema import JsonSchema
import uuid

from .. schema import GraphEmbeddings
from .. schema import graph_embeddings_store_queue

from . subscriber import Subscriber
from . socket import SocketEndpoint
from . serialize import serialize_graph_embeddings

class GraphEmbeddingsStreamEndpoint(SocketEndpoint):

    def __init__(
            self, pulsar_host, auth, path="/api/v1/stream/graph-embeddings"
    ):

        super(GraphEmbeddingsStreamEndpoint, self).__init__(
            endpoint_path=path, auth=auth,
        )

        self.pulsar_host=pulsar_host

        self.subscriber = Subscriber(
            self.pulsar_host, graph_embeddings_store_queue,
            "api-gateway", "api-gateway",
            schema=JsonSchema(GraphEmbeddings)
        )

    async def start(self):

        self.subscriber.start()

    async def async_thread(self, ws, running):

        id = str(uuid.uuid4())

        q = self.subscriber.subscribe_all(id)

        while running.get():
            try:
                resp = await asyncio.to_thread(q.get, timeout=0.5)
                await ws.send_json(serialize_graph_embeddings(resp))

            except queue.Empty:
                continue

            except Exception as e:
                print(f"Exception: {str(e)}", flush=True)
                break

        self.subscriber.unsubscribe_all(id)

        running.stop()

