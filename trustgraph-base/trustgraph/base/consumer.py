
# Consumer is similar to subscriber: It takes information from a queue
# and passes on to a processor function.  This is the main receiving
# loop for TrustGraph processors.  Incorporates retry functionality

# Note: there is a 'defect' in the system which is tolerated, althought
# the processing handlers are async functions, ideally implementation
# would use all async code.  In practice if the processor only implements
# one handler, and a single thread of concurrency, nothing too outrageous
# will happen if synchronous / blocking code is used

import asyncio
import time
import logging

from .. exceptions import TooManyRequests

# Module logger
logger = logging.getLogger(__name__)

# Timeout exception - can come from different backends
class TimeoutError(Exception):
    pass

class Consumer:

    def __init__(
            self, taskgroup, flow, backend, topic, subscriber, schema,
            handler,
            metrics = None,
            start_of_messages=False,
            rate_limit_retry_time = 10, rate_limit_timeout = 7200,
            reconnect_time = 5,
            concurrency = 1, # Number of concurrent requests to handle
    ):

        self.taskgroup = taskgroup
        self.flow = flow
        self.backend = backend  # Changed from 'client' to 'backend'
        self.topic = topic
        self.subscriber = subscriber
        self.schema = schema
        self.handler = handler

        self.rate_limit_retry_time = rate_limit_retry_time
        self.rate_limit_timeout = rate_limit_timeout

        self.reconnect_time = 5

        self.start_of_messages = start_of_messages

        self.running = True
        self.consumer_task = None

        self.concurrency = concurrency

        self.metrics = metrics

        self.consumer = None

    def __del__(self):
        self.running = False

        if hasattr(self, "consumer"):
            if self.consumer:
                self.consumer.unsubscribe()
                self.consumer.close()
                self.consumer = None

    async def stop(self):

        self.running = False

        if self.consumer_task:
            await self.consumer_task

        self.consumer_task = None

    async def start(self):

        self.running = True

        # Puts it in the stopped state, the run thread should set running
        if self.metrics:
            self.metrics.state("stopped")

        self.consumer_task = self.taskgroup.create_task(self.consumer_run())

    async def consumer_run(self):

        while self.running:

            if self.metrics:
                self.metrics.state("stopped")

            try:

                logger.info(f"Subscribing to topic: {self.topic}")

                # Determine initial position
                if self.start_of_messages:
                    initial_pos = 'earliest'
                else:
                    initial_pos = 'latest'

                # Create consumer via backend
                self.consumer = await asyncio.to_thread(
                    self.backend.create_consumer,
                    topic = self.topic,
                    subscription = self.subscriber,
                    schema = self.schema,
                    initial_position = initial_pos,
                    consumer_type = 'shared',
                )

            except Exception as e:

                logger.error(f"Consumer subscription exception: {e}", exc_info=True)
                await asyncio.sleep(self.reconnect_time)
                continue

            logger.info(f"Successfully subscribed to topic: {self.topic}")

            if self.metrics:
                self.metrics.state("running")

            try:

                logger.info(f"Starting {self.concurrency} receiver threads")

                async with asyncio.TaskGroup() as tg:

                    tasks = []

                    for i in range(0, self.concurrency):
                        tasks.append(
                            tg.create_task(self.consume_from_queue())
                        )

                if self.metrics:
                    self.metrics.state("stopped")

            except Exception as e:

                logger.error(f"Consumer loop exception: {e}", exc_info=True)
                self.consumer.unsubscribe()
                self.consumer.close()
                self.consumer = None
                await asyncio.sleep(self.reconnect_time)
                continue

        if self.consumer:
            self.consumer.unsubscribe()
            self.consumer.close()

    async def consume_from_queue(self):

        while self.running:

            try:
                msg = await asyncio.to_thread(
                    self.consumer.receive,
                    timeout_millis=2000
                )
            except Exception as e:
                # Handle timeout from any backend
                if 'timeout' in str(type(e)).lower() or 'timeout' in str(e).lower():
                    continue
                raise e

            await self.handle_one_from_queue(msg)

    async def handle_one_from_queue(self, msg):

        expiry = time.time() + self.rate_limit_timeout

        # This loop is for retry on rate-limit / resource limits
        while self.running:

            if time.time() > expiry:

                logger.warning("Gave up waiting for rate-limit retry")

                # Message failed to be processed, this causes it to
                # be retried
                self.consumer.negative_acknowledge(msg)

                if self.metrics:
                    self.metrics.process("error")

                # Break out of retry loop, processes next message
                break

            try:

                logger.debug("Processing message...")

                if self.metrics:

                    with self.metrics.record_time():
                        await self.handler(msg, self, self.flow)

                else:
                    await self.handler(msg, self, self.flow)

                logger.debug("Message processed successfully")

                # Acknowledge successful processing of the message
                self.consumer.acknowledge(msg)

                if self.metrics:
                    self.metrics.process("success")

                # Break out of retry loop
                break

            except TooManyRequests:

                logger.warning("Rate limit exceeded, will retry...")

                if self.metrics:
                    self.metrics.rate_limit()

                # Sleep
                await asyncio.sleep(self.rate_limit_retry_time)

                # Contine from retry loop, just causes a reprocessing
                continue

            except Exception as e:

                logger.error(f"Message processing exception: {e}", exc_info=True)

                # Message failed to be processed, this causes it to
                # be retried
                self.consumer.negative_acknowledge(msg)

                if self.metrics:
                    self.metrics.process("error")

                # Break out of retry loop, processes next message
                break
