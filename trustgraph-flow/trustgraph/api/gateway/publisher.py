
import asyncio
import aiopulsar

class Publisher:

    def __init__(self, pulsar_host, topic, schema=None, max_size=10,
                 chunking_enabled=False):
        self.pulsar_host = pulsar_host
        self.topic = topic
        self.schema = schema
        self.q = asyncio.Queue(maxsize=max_size)
        self.chunking_enabled = chunking_enabled

    async def run(self):

        while True:

            try:
                async with aiopulsar.connect(self.pulsar_host) as client:
                    async with client.create_producer(
                            topic=self.topic,
                            schema=self.schema,
                            chunking_enabled=self.chunking_enabled,
                    ) as producer:
                        while True:
                            id, item = await self.q.get()

                            if id:
                                await producer.send(item, { "id": id })
                            else:
                                await producer.send(item)

            except Exception as e:
                print("Exception:", e, flush=True)

            # If handler drops out, sleep a retry
            await asyncio.sleep(2)

    async def send(self, id, msg):
        await self.q.put((id, msg))
