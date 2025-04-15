
import asyncio
import time

from .. exceptions import TooManyRequests

class Consumer:

    def __init__(
            self, taskgroup, client, queue, subscriber, schema,
            handler, rate_limit_retry_time = 10,
            rate_limit_timeout = 7200, metrics = None,
            start_of_messages=False,
    ):

        self.taskgroup = taskgroup
        self.client = client
        self.queue = queue
        self.subscriber = subscriber
        self.schema = schema
        self.handler = handler
        self.rate_limit_retry_time = rate_limit_retry_time
        self.rate_limit_timeout = rate_limit_timeout
        self.start_of_messages = start_of_messages

        self.running = True
        self.task = None

        self.metrics = metrics

    async def stop(self):

        self.running = False

    async def start(self):

        self.running = True

        self.consumer = self.client.subscribe(
            self.queue, self.subscriber, self.schema,
            start_of_messages = self.start_of_messages,
        )

        print("Subscribed.", flush=True)

        # Puts it in the stopped state, the run thread should set running
        if self.metrics:
            self.metrics.state("stopped")

        self.task = self.taskgroup.create_task(self.run())

        print("Subscriber started", flush=True)

    async def run(self):

        if self.metrics:
            self.metrics.state("running")

        while self.running:

            msg = await asyncio.to_thread(self.consumer.receive)

            expiry = time.time() + self.rate_limit_timeout

            # This loop is for retry on rate-limit / resource limits
            while True:

                if time.time() > expiry:

                    print("Gave up waiting for rate-limit retry", flush=True)

                    # Message failed to be processed, this causes it to
                    # be retried
                    self.consumer.negative_acknowledge(msg)

                    if self.metrics:
                        self.metrics.process("error")

                    # Break out of retry loop, processes next message
                    break

                try:

                    print("Handle...", flush=True)

                    if self.metrics:

                        with self.metrics.record_time():
                            await self.handler(msg, self.consumer)

                    else:
                        await self.handler(msg, self.consumer)

                    print("Handled.", flush=True)

                    # Acknowledge successful processing of the message
                    self.consumer.acknowledge(msg)

                    if self.metrics:
                        self.metrics.process("success")

                    # Break out of retry loop
                    break

                except TooManyRequests:

                    print("TooManyRequests: will retry...", flush=True)

                    # FIXME
                    if self.metrics:
                        self.metrics.rate_limit()

                    # Sleep
                    await asyncio.sleep(self.rate_limit_retry)

                    # Contine from retry loop, just causes a reprocessing
                    continue

                except Exception as e:

                    print("Exception:", e, flush=True)

                    # Message failed to be processed, this causes it to
                    # be retried
                    self.consumer.negative_acknowledge(msg)

                    if self.metrics:
                        self.metrics.process("error")

                    # Break out of retry loop, processes next message
                    break

        if self.metrics:
            self.metrics.state("stopped")
