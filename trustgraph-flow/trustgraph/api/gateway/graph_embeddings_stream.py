
import asyncio
from pulsar.schema import JsonSchema
import uuid

from ... schema import GraphEmbeddings
from ... schema import graph_embeddings_store_queue

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

    async def start(self, client):

        self.task = asyncio.create_task(
            self.subscriber.run(client)
        )

    async def async_thread(self, ws, running):

        id = str(uuid.uuid4())

        q = await self.subscriber.subscribe_all(id)

        while running.get():
            try:
                resp = await asyncio.wait_for(q.get(), 0.5)
                await ws.send_json(serialize_graph_embeddings(resp))

            except TimeoutError:
                continue

            except Exception as e:
                print(f"Exception: {str(e)}", flush=True)
                break

        await self.subscriber.unsubscribe_all(id)

        running.stop()

