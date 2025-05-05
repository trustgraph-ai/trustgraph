
from pulsar.schema import JsonSchema
import asyncio

class Producer:

    def __init__(self, client, topic, schema, metrics=None,
                 chunking_enabled=True):

        self.client = client
        self.topic = topic
        self.schema = schema

        self.metrics = metrics

        self.running = True
        self.producer = None

        self.chunking_enabled = chunking_enabled

    def __del__(self):

        self.running = False

        if hasattr(self, "producer"):
            if self.producer:
                self.producer.close()

    async def start(self):
        self.running = True

    async def stop(self):
        self.running = False

    async def send(self, msg, properties={}):

        if not self.running: return

        while self.running and self.producer is None:

            try:
                print("Connect publisher to", self.topic, "...", flush=True)
                self.producer = self.client.create_producer(
                    topic = self.topic,
                    schema = JsonSchema(self.schema),
                    chunking_enabled = self.chunking_enabled,
                )
                print("Connected to", self.topic, flush=True)
            except Exception as e:
                print("Exception:", e, flush=True)
                await asyncio.sleep(2)

            if not self.running: break

        while self.running:

            try:

                await asyncio.to_thread(
                    self.producer.send,
                    msg, properties
                )

                if self.metrics:
                    self.metrics.inc()

                # Delivery success, break out of loop
                break

            except Exception as e:
                print("Exception:", e, flush=True)
                self.producer.close()
                self.producer = None

