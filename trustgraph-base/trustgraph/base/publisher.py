
from pulsar.schema import JsonSchema

import asyncio
import time
import pulsar
import logging

# Module logger
logger = logging.getLogger(__name__)

class Publisher:

    def __init__(self, client, topic, schema=None, max_size=10,
                 chunking_enabled=True, drain_timeout=5.0):
        self.client = client
        self.topic = topic
        self.schema = schema
        self.q = asyncio.Queue(maxsize=max_size)
        self.chunking_enabled = chunking_enabled
        self.running = True
        self.draining = False  # New state for graceful shutdown
        self.task = None
        self.drain_timeout = drain_timeout

    async def start(self):
        self.task = asyncio.create_task(self.run())

    async def stop(self):
        """Initiate graceful shutdown with draining"""
        self.running = False
        self.draining = True

        if self.task:
            # Wait for run() to complete draining
            await self.task

    async def join(self):
        await self.stop()

        if self.task:
            await self.task

    async def run(self):

        while self.running or self.draining:

            try:

                producer = self.client.create_producer(
                    topic=self.topic,
                    schema=JsonSchema(self.schema),
                    chunking_enabled=self.chunking_enabled,
                )

                drain_end_time = None

                while self.running or self.draining:

                    try:
                        # Start drain timeout when entering drain mode
                        if self.draining and drain_end_time is None:
                            drain_end_time = time.time() + self.drain_timeout
                            logger.info(f"Publisher entering drain mode, timeout={self.drain_timeout}s")
                        
                        # Check drain timeout
                        if self.draining and drain_end_time and time.time() > drain_end_time:
                            if not self.q.empty():
                                logger.warning(f"Drain timeout reached with {self.q.qsize()} messages remaining")
                            self.draining = False
                            break
                        
                        # Calculate wait timeout based on mode
                        if self.draining:
                            # Shorter timeout during draining to exit quickly when empty
                            timeout = min(0.1, drain_end_time - time.time()) if drain_end_time else 0.1
                        else:
                            # Normal operation timeout
                            timeout = 0.25

                        id, item = await asyncio.wait_for(
                            self.q.get(),
                            timeout=timeout
                        )
                    except asyncio.TimeoutError:
                        # If draining and queue is empty, we're done
                        if self.draining and self.q.empty():
                            logger.info("Publisher queue drained successfully")
                            self.draining = False
                            break
                        continue
                    except asyncio.QueueEmpty:
                        # If draining and queue is empty, we're done
                        if self.draining and self.q.empty():
                            logger.info("Publisher queue drained successfully")
                            self.draining = False
                            break
                        continue

                    if id:
                        producer.send(item, { "id": id })
                    else:
                        producer.send(item)
                
                # Flush producer before closing
                producer.flush()
                producer.close()

            except Exception as e:
                logger.error(f"Exception in publisher: {e}", exc_info=True)

            if not self.running and not self.draining:
                return

            # If handler drops out, sleep a retry
            await asyncio.sleep(1)

    async def send(self, id, item):
        if self.draining:
            # Optionally reject new messages during drain
            raise RuntimeError("Publisher is shutting down, not accepting new messages")
        await self.q.put((id, item))

