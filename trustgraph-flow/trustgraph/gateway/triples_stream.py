
import asyncio
import queue
from pulsar.schema import JsonSchema
import uuid

from .. schema import Triples
from .. schema import triples_store_queue
from .. base import Subscriber

from . socket import SocketEndpoint
from . serialize import serialize_triples

class TriplesStreamEndpoint(SocketEndpoint):

    def __init__(self, pulsar_client, auth, path="/api/v1/stream/triples"):

        super(TriplesStreamEndpoint, self).__init__(
            endpoint_path=path, auth=auth,
        )

        self.pulsar_client=pulsar_client

        self.subscriber = Subscriber(
            self.pulsar_client, triples_store_queue,
            "api-gateway", "api-gateway",
            schema=JsonSchema(Triples)
        )

    async def listener(self, ws, running):

        worker = asyncio.create_task(
            self.async_thread(ws, running)
        )

        await super(TriplesStreamEndpoint, self).listener(ws, running)

        await worker

    async def start(self):

        self.subscriber.start()

    async def async_thread(self, ws, running):

        id = str(uuid.uuid4())

        q = self.subscriber.subscribe_all(id)

        while running.get():
            try:
                resp = await asyncio.to_thread(q.get, timeout=0.5)
                await ws.send_json(serialize_triples(resp))

            except TimeoutError:
                continue

            except queue.Empty:
                continue

            except Exception as e:
                print(f"Exception: {str(e)}", flush=True)
                break

        self.subscriber.unsubscribe_all(id)

        running.stop()

