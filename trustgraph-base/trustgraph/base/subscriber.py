
from pulsar.schema import JsonSchema
import asyncio
import _pulsar
import time

class Subscriber:

    def __init__(self, client, topic, subscription, consumer_name,
                 schema=None, max_size=100, metrics=None):
        self.client = client
        self.topic = topic
        self.subscription = subscription
        self.consumer_name = consumer_name
        self.schema = schema
        self.q = {}
        self.full = {}
        self.max_size = max_size
        self.lock = asyncio.Lock()
        self.running = True
        self.metrics = metrics

    def __del__(self):
        self.running = False

    async def start(self):
        self.task = asyncio.create_task(self.run())

    async def stop(self):
        self.running = False
        await self.task

    async def join(self):
        await self.stop()
        await self.task

    async def run(self):

        consumer = None

        while self.running:

            if self.metrics:
                self.metrics.state("stopped")

            try:

                # FIXME: Create consumer in start  method so we know
                # it is definitely running when start completes
                consumer = self.client.subscribe(
                    topic = self.topic,
                    subscription_name = self.subscription,
                    consumer_name = self.consumer_name,
                    schema = JsonSchema(self.schema),
                )

                if self.metrics:
                    self.metrics.state("running")

                print("Subscriber running...", flush=True)

                while self.running:

                    try:
                        msg = await asyncio.to_thread(
                            consumer.receive,
                            timeout_millis=250
                        )
                    except _pulsar.Timeout:
                        continue
                    except Exception as e:
                        print("Exception:", e, flush=True)
                        print(type(e))
                        raise e

                    if self.metrics:
                        self.metrics.received()

                    # Acknowledge successful reception of the message
                    consumer.acknowledge(msg)

                    try:
                        id = msg.properties()["id"]
                    except:
                        id = None

                    value = msg.value()

                    async with self.lock:

                        # FIXME: Hard-coded timeouts

                        if id in self.q:

                            try:
                                # FIXME: Timeout means data goes missing
                                await asyncio.wait_for(
                                    self.q[id].put(value),
                                    timeout=1
                                )

                            except Exception as e:
                                self.metrics.dropped()
                                print("Q Put:", e, flush=True)

                        for q in self.full.values():
                            try:
                                # FIXME: Timeout means data goes missing
                                await asyncio.wait_for(
                                    q.put(value),
                                    timeout=1
                                )
                            except Exception as e:
                                self.metrics.dropped()
                                print("Q Put:", e, flush=True)

            except Exception as e:
                print("Subscriber exception:", e, flush=True)

            finally:

                if consumer:
                    consumer.close()
                    consumer = None
                
         
            if self.metrics:
                self.metrics.state("stopped")

            if not self.running:
                return
            
            # If handler drops out, sleep a retry
            await asyncio.sleep(1)

    async def subscribe(self, id):

        async with self.lock:

            q = asyncio.Queue(maxsize=self.max_size)
            self.q[id] = q

        return q

    async def unsubscribe(self, id):
        
        async with self.lock:

            if id in self.q:
#                self.q[id].shutdown(immediate=True)
                del self.q[id]
    
    async def subscribe_all(self, id):

        async with self.lock:

            q = asyncio.Queue(maxsize=self.max_size)
            self.full[id] = q

        return q

    async def unsubscribe_all(self, id):

        async with self.lock:

            if id in self.full:
#                self.full[id].shutdown(immediate=True)
                del self.full[id]

