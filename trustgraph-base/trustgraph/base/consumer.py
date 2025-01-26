
from pulsar.schema import JsonSchema
import pulsar
from prometheus_client import Histogram, Info, Counter, Enum
import time

from . base_processor import BaseProcessor
from .. exceptions import TooManyRequests

default_rate_limit_retry = 10
default_rate_limit_timeout = 7200

class Consumer(BaseProcessor):

    def __init__(self, **params):

        if not hasattr(__class__, "state_metric"):
            __class__.state_metric = Enum(
                'processor_state', 'Processor state',
                states=['starting', 'running', 'stopped']
            )
            __class__.state_metric.state('starting')

        __class__.state_metric.state('starting')

        super(Consumer, self).__init__(**params)

        self.input_queue = params.get("input_queue")
        self.subscriber = params.get("subscriber")
        self.input_schema = params.get("input_schema")

        self.rate_limit_retry = params.get(
            "rate_limit_retry", default_rate_limit_retry
        )
        self.rate_limit_timeout = params.get(
            "rate_limit_timeout", default_rate_limit_timeout
        )

        if self.input_schema == None:
            raise RuntimeError("input_schema must be specified")

        if not hasattr(__class__, "request_metric"):
            __class__.request_metric = Histogram(
                'request_latency', 'Request latency (seconds)'
            )

        if not hasattr(__class__, "pubsub_metric"):
            __class__.pubsub_metric = Info(
                'pubsub', 'Pub/sub configuration'
            )

        if not hasattr(__class__, "processing_metric"):
            __class__.processing_metric = Counter(
                'processing_count', 'Processing count', ["status"]
            )

        if not hasattr(__class__, "retry_metric"):
            __class__.retry_metric = Counter(
                'retry_count', 'Retry count',
            )

        __class__.pubsub_metric.info({
            "input_queue": self.input_queue,
            "subscriber": self.subscriber,
            "input_schema": self.input_schema.__name__,
            "rate_limit_retry": str(self.rate_limit_retry),
            "rate_limit_timeout": str(self.rate_limit_timeout),
        })

        self.consumer = self.client.subscribe(
            self.input_queue, self.subscriber,
            consumer_type=pulsar.ConsumerType.Shared,
            schema=JsonSchema(self.input_schema),
        )

        print("Initialised consumer.", flush=True)

    def run(self):

        __class__.state_metric.state('running')

        while True:

            msg = self.consumer.receive()

            expiry = time.time() + self.rate_limit_timeout

            # This loop is for retry on rate-limit / resource limits
            while True:

                if time.time() > expiry:

                    print("Gave up waiting for rate-limit retry", flush=True)

                    # Message failed to be processed, this causes it to
                    # be retried
                    self.consumer.negative_acknowledge(msg)

                    __class__.processing_metric.labels(status="error").inc()

                    # Break out of retry loop, processes next message
                    break

                try:

                    with __class__.request_metric.time():
                        self.handle(msg)

                    # Acknowledge successful processing of the message
                    self.consumer.acknowledge(msg)

                    __class__.processing_metric.labels(status="success").inc()

                    # Break out of retry loop
                    break

                except TooManyRequests:

                    print("TooManyRequests: will retry...", flush=True)

                    __class__.retry_metric.inc()

                    # Sleep
                    time.sleep(self.rate_limit_retry)

                    # Contine from retry loop, just causes a reprocessing
                    continue
                
                except Exception as e:

                    print("Exception:", e, flush=True)

                    # Message failed to be processed, this causes it to
                    # be retried
                    self.consumer.negative_acknowledge(msg)

                    __class__.processing_metric.labels(status="error").inc()

                    # Break out of retry loop, processes next message
                    break

    @staticmethod
    def add_args(parser, default_input_queue, default_subscriber):

        BaseProcessor.add_args(parser)

        parser.add_argument(
            '-i', '--input-queue',
            default=default_input_queue,
            help=f'Input queue (default: {default_input_queue})'
        )

        parser.add_argument(
            '-s', '--subscriber',
            default=default_subscriber,
            help=f'Queue subscriber name (default: {default_subscriber})'
        )

        parser.add_argument(
            '--rate-limit-retry',
            type=int,
            default=default_rate_limit_retry,
            help=f'Rate limit retry (default: {default_rate_limit_retry})'
        )

        parser.add_argument(
            '--rate-limit-timeout',
            type=int,
            default=default_rate_limit_timeout,
            help=f'Rate limit timeout (default: {default_rate_limit_timeout})'
        )

