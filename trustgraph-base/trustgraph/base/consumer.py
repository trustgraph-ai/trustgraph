
import asyncio
import time

from .. exceptions import TooManyRequests

class Consumer:

    def __init__(
            self, taskgroup, client, queue, subscriber, schema,
            handler
    ):

        self.taskgroup = taskgroup
        self.client = client
        self.queue = queue
        self.subscriber = subscriber
        self.schema = schema
        self.handler = handler

        self.running = True
        self.task = None

    async def start(self):

        self.running = True

        self.consumer = self.client.subscribe(
            self.queue, self.subscriber, self.schema
        )

        self.task = self.taskgroup.create_task(self.run())


    async def run(self):

        while self.running:

            msg = await asyncio.to_thread(self.consumer.receive)

#             expiry = time.time() + self.rate_limit_timeout
            expiry = time.time() + 10

            # This loop is for retry on rate-limit / resource limits
            while True:

                if time.time() > expiry:

                    print("Gave up waiting for rate-limit retry", flush=True)

                    # Message failed to be processed, this causes it to
                    # be retried
                    self.consumer.negative_acknowledge(msg)

                    # FIXME
#                    __class__.processing_metric.labels(status="error").inc()

                    # Break out of retry loop, processes next message
                    break

                try:

                    print("Handle...")
                    # FIXME
#                    with __class__.request_metric.time():
                    await self.handler(msg, self.consumer)
                    print("Handled.")

                    # Acknowledge successful processing of the message
                    self.consumer.acknowledge(msg)

#                    __class__.processing_metric.labels(status="success").inc()

                    # Break out of retry loop
                    break

                except TooManyRequests:

                    print("TooManyRequests: will retry...", flush=True)

                    # FIXME
#                     __class__.rate_limit_metric.inc()

                    # Sleep
                    time.sleep(self.rate_limit_retry)

                    # Contine from retry loop, just causes a reprocessing
                    continue

                except Exception as e:

                    print("Exception:", e, flush=True)

                    # Message failed to be processed, this causes it to
                    # be retried
                    self.consumer.negative_acknowledge(msg)

#                    __class__.processing_metric.labels(status="error").inc()

                    # Break out of retry loop, processes next message
                    break

