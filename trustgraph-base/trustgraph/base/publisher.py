
from pulsar.schema import JsonSchema

import asyncio
import time
import pulsar

class Publisher:

    def __init__(self, client, topic, schema=None, max_size=10,
                 chunking_enabled=True):
        self.client = client
        self.topic = topic
        self.schema = schema
        self.q = asyncio.Queue(maxsize=max_size)
        self.chunking_enabled = chunking_enabled
        self.running = True
        self.task = None

    async def start(self):
        self.task = asyncio.create_task(self.run())

    async def stop(self):
        self.running = False

        if self.task:
            await self.task

    async def join(self):
        await self.stop()

        if self.task:
            await self.task

    async def run(self):

        while self.running:

            try:

                producer = self.client.create_producer(
                    topic=self.topic,
                    schema=JsonSchema(self.schema),
                    chunking_enabled=self.chunking_enabled,
                )

                while self.running:

                    try:
                        id, item = await asyncio.wait_for(
                            self.q.get(),
                            timeout=0.25
                        )
                    except asyncio.TimeoutError:
                        continue
                    except asyncio.QueueEmpty:
                        continue

                    if id:
                        producer.send(item, { "id": id })
                    else:
                        producer.send(item)

            except Exception as e:
                print("Exception:", e, flush=True)

            if not self.running:
                return

            # If handler drops out, sleep a retry
            await asyncio.sleep(1)

    async def send(self, id, item):
        await self.q.put((id, item))

