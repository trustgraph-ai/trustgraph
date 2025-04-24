
from pulsar.schema import JsonSchema
import pulsar
import _pulsar
import asyncio
import time

from .. exceptions import TooManyRequests

class Consumer:

    def __init__(
            self, taskgroup, flow, client, topic, subscriber, schema,
            handler, 
            metrics = None,
            start_of_messages=False,
            rate_limit_retry_time = 10, rate_limit_timeout = 7200,
            reconnect_time = 5,
    ):

        self.taskgroup = taskgroup
        self.flow = flow
        self.client = client
        self.topic = topic
        self.subscriber = subscriber
        self.schema = schema
        self.handler = handler

        self.rate_limit_retry_time = rate_limit_retry_time
        self.rate_limit_timeout = rate_limit_timeout

        self.reconnect_time = 5

        self.start_of_messages = start_of_messages

        self.running = True
        self.task = None

        self.metrics = metrics

        self.consumer = None

    def __del__(self):
        self.running = False

        if hasattr(self, "consumer"):
            if self.consumer:
                self.consumer.close()

    async def stop(self):

        self.running = False
        await self.task

    async def start(self):

        self.running = True

        # Puts it in the stopped state, the run thread should set running
        if self.metrics:
            self.metrics.state("stopped")

        self.task = self.taskgroup.create_task(self.run())

    async def run(self):

        while self.running:

            if self.metrics:
                self.metrics.state("stopped")

            try:

                print(self.topic, "subscribing...", flush=True)

                if self.start_of_messages:
                    pos = pulsar.InitialPosition.Earliest
                else:
                    pos = pulsar.InitialPosition.Latest

                self.consumer = await asyncio.to_thread(
                    self.client.subscribe,
                    topic = self.topic,
                    subscription_name = self.subscriber,
                    schema = JsonSchema(self.schema),
                    initial_position = pos,
                    consumer_type = pulsar.ConsumerType.Shared,
                )

            except Exception as e:

                print("consumer subs Exception:", e, flush=True)
                await asyncio.sleep(self.reconnect_time)
                continue

            print(self.topic, "subscribed", flush=True)

            if self.metrics:
                self.metrics.state("running")

            try:

                await self.consume()

                if self.metrics:
                    self.metrics.state("stopped")

            except Exception as e:

                print("consumer loop exception:", e, flush=True)
                self.consumer.close()
                self.consumer = None
                await asyncio.sleep(self.reconnect_time)
                continue

    async def consume(self):

        while self.running:

            try:
                msg = await asyncio.to_thread(
                    self.consumer.receive,
                    timeout_millis=2000
                )
            except _pulsar.Timeout:
                continue
            except Exception as e:
                raise e

            expiry = time.time() + self.rate_limit_timeout

            # This loop is for retry on rate-limit / resource limits
            while self.running:

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
                            await self.handler(msg, self, self.flow)

                    else:
                        await self.handler(msg, self, self.flow)

                    print("Handled.", flush=True)

                    # Acknowledge successful processing of the message
                    self.consumer.acknowledge(msg)

                    if self.metrics:
                        self.metrics.process("success")

                    # Break out of retry loop
                    break

                except TooManyRequests:

                    print("TooManyRequests: will retry...", flush=True)

                    if self.metrics:
                        self.metrics.rate_limit()

                    # Sleep
                    await asyncio.sleep(self.rate_limit_retry_time)

                    # Contine from retry loop, just causes a reprocessing
                    continue

                except Exception as e:

                    print("consume exception:", e, flush=True)

                    # Message failed to be processed, this causes it to
                    # be retried
                    self.consumer.negative_acknowledge(msg)

                    if self.metrics:
                        self.metrics.process("error")

                    # Break out of retry loop, processes next message
                    break
