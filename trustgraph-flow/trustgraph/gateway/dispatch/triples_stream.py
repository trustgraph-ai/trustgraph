
import asyncio
import queue
import uuid

from ... schema import Triples
from ... base import Subscriber

from . serialize import serialize_triples

class TriplesStream:

    def __init__(self, ws, running, pulsar_client, queue):

        self.ws = ws
        self.running = runnning
        self.pulsar_client = pulsar_client
        self.queue = queue

    async def destroy(self):
        self.running.stop()
        self.ws.close()

    async def receive(self, msg):
        print(msg.data)

    async def run(self, ws, running):

        self.subscriber = Subscriber(
            pulsar_client, queue,
            "api-gateway", "api-gateway",
            schema=Triples
        )

        await self.subscriber.start()

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

        await ws.close()
        running.stop()

