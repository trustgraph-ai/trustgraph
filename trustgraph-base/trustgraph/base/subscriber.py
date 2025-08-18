
# Subscriber is similar to consumer: It provides a service to take stuff
# off of a queue and make it available using an internal broker system,
# so suitable for when multiple recipients are reading from the same queue

from pulsar.schema import JsonSchema
import asyncio
import _pulsar
import time
import logging

# Module logger
logger = logging.getLogger(__name__)

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
        self.task = None

        self.consumer = None

    def __del__(self):

        self.running = False

    async def start(self):

        self.consumer = self.client.subscribe(
            topic = self.topic,
            subscription_name = self.subscription,
            consumer_name = self.consumer_name,
            schema = JsonSchema(self.schema),
        )

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

            if self.metrics:
                self.metrics.state("stopped")

            try:

                if self.metrics:
                    self.metrics.state("running")

                logger.info("Subscriber running...")

                while self.running:

                    try:
                        msg = await asyncio.to_thread(
                            self.consumer.receive,
                            timeout_millis=250
                        )
                    except _pulsar.Timeout:
                        continue
                    except Exception as e:
                        logger.error(f"Exception in subscriber receive: {e}", exc_info=True)
                        raise e

                    if self.metrics:
                        self.metrics.received()

                    # Acknowledge successful reception of the message
                    self.consumer.acknowledge(msg)

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
                                logger.warning(f"Failed to put message in queue: {e}")

                        for q in self.full.values():
                            try:
                                # FIXME: Timeout means data goes missing
                                await asyncio.wait_for(
                                    q.put(value),
                                    timeout=1
                                )
                            except Exception as e:
                                self.metrics.dropped()
                                logger.warning(f"Failed to put message in full queue: {e}")

            except Exception as e:
                logger.error(f"Subscriber exception: {e}", exc_info=True)

            finally:

                if self.consumer:
                    self.consumer.unsubscribe()
                    self.consumer.close()
                    self.consumer = None
                
         
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

