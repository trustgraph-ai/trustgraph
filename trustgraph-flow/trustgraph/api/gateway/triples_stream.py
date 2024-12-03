
import asyncio
from pulsar.schema import JsonSchema
import uuid

from ... schema import Triples
from ... schema import triples_store_queue

from . subscriber import Subscriber
from . socket import SocketEndpoint
from . serialize import serialize_triples

class TriplesStreamEndpoint(SocketEndpoint):

    def __init__(self, pulsar_host, auth, path="/api/v1/stream/triples"):

        super(TriplesStreamEndpoint, self).__init__(
            endpoint_path=path, auth=auth,
        )

        self.pulsar_host=pulsar_host

        self.subscriber = Subscriber(
            self.pulsar_host, triples_store_queue,
            "api-gateway", "api-gateway",
            schema=JsonSchema(Triples)
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
                await ws.send_json(serialize_triples(resp))

            except TimeoutError:
                continue

            except Exception as e:
                print(f"Exception: {str(e)}", flush=True)
                break

        await self.subscriber.unsubscribe_all(id)

        running.stop()

