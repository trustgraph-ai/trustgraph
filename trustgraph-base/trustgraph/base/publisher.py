
import asyncio
import time
import pulsar

class Publisher:

    def __init__(self, pulsar_client, topic, schema=None, max_size=10,
                 chunking_enabled=True):
        self.client = pulsar_client
        self.topic = topic
        self.schema = schema
        self.q = asyncio.Queue(maxsize=max_size)
        self.chunking_enabled = chunking_enabled
        self.running = True

    async def start(self):
        self.task = asyncio.create_task(self.run())
        await self.task.start()

    async def stop(self):
        self.running = False

    async def join(self):
        await self.stop()
        await self.task

    async def run(self):

        while self.running:

            try:
                producer = self.client.create_producer(
                    topic=self.topic,
                    schema=self.schema,
                    chunking_enabled=self.chunking_enabled,
                )

                while self.running:

                    try:
                        id, item = asyncio.wait_for(
                            self.q.get(),
                            timeout=0.5
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

            # If handler drops out, sleep a retry
            time.sleep(2)

    async def send(self, id, item):
        await self.q.put((id, item))

