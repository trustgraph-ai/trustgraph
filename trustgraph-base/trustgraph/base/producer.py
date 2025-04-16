
import asyncio

class Producer:

    def __init__(self, client, queue, schema, metrics=None):
        self.client = client
        self.queue = queue
        self.schema = schema

        self.metrics = metrics

        self.running = True
        self.producer = None

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
                print("Connect publisher to", self.queue, "...", flush=True)
                self.producer = self.client.publish(self.queue, self.schema)
                print("Connected to", self.queue, flush=True)
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

