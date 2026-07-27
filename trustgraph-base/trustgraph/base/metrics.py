from __future__ import annotations

from typing import Any

from prometheus_client import start_http_server, Info, Enum, Histogram
from prometheus_client import Counter

class ConsumerMetrics:

    def __init__(self, processor: str, consumer: str,
                 workspace: str | None = None,
                 flow: str | None = None) -> None:

        self.processor = processor
        self.consumer = consumer

        if not hasattr(__class__, "state_metric"):
            __class__.state_metric = Enum(
                'consumer_state', 'Consumer state',
                ["processor", "consumer"],
                states=['stopped', 'running']
            )

        if not hasattr(__class__, "request_metric"):
            __class__.request_metric = Histogram(
                'request_latency', 'Request latency (seconds)',
                ["processor", "consumer"],
            )

        if not hasattr(__class__, "processing_metric"):
            __class__.processing_metric = Counter(
                'processing_count', 'Processing count',
                ["processor", "consumer", "status"],
            )

        if not hasattr(__class__, "rate_limit_metric"):
            __class__.rate_limit_metric = Counter(
                'rate_limit_count', 'Rate limit event count',
                ["processor", "consumer"],
            )

        __class__.request_metric.labels(
            processor=self.processor, consumer=self.consumer,
        )
        __class__.processing_metric.labels(
            processor=self.processor, consumer=self.consumer,
            status="ok",
        )
        __class__.processing_metric.labels(
            processor=self.processor, consumer=self.consumer,
            status="error",
        )
        __class__.rate_limit_metric.labels(
            processor=self.processor, consumer=self.consumer,
        )

    def process(self, status: str) -> None:
        __class__.processing_metric.labels(
            processor=self.processor,
            consumer=self.consumer, status=status,
        ).inc()

    def rate_limit(self) -> None:
        __class__.rate_limit_metric.labels(
            processor=self.processor,
            consumer=self.consumer,
        ).inc()

    def state(self, state: str) -> None:
        __class__.state_metric.labels(
            processor=self.processor,
            consumer=self.consumer,
        ).state(state)

    def record_time(self) -> Any:
        return __class__.request_metric.labels(
            processor=self.processor, consumer=self.consumer,
        ).time()

class ProducerMetrics:

    def __init__(self, processor: str, producer: str,
                 workspace: str | None = None,
                 flow: str | None = None) -> None:

        self.processor = processor
        self.producer = producer

        if not hasattr(__class__, "producer_metric"):
            __class__.producer_metric = Counter(
                'producer_count', 'Output items produced',
                ["processor", "producer"],
            )

        __class__.producer_metric.labels(
            processor=self.processor, producer=self.producer,
        )

    def inc(self) -> None:
        __class__.producer_metric.labels(
            processor=self.processor,
            producer=self.producer,
        ).inc()

class ProcessorMetrics:
    def __init__(self, processor: str) -> None:

        self.processor = processor

        if not hasattr(__class__, "processor_metric"):
            __class__.processor_metric = Info(
                'processor', 'Processor configuration',
                ["processor"]
            )

    def info(self, info: dict[str, str]) -> None:
        __class__.processor_metric.labels(
            processor = self.processor
        ).info(info)

class SubscriberMetrics:

    def __init__(self, processor: str, subscriber: str,
                 workspace: str | None = None,
                 flow: str | None = None) -> None:

        self.processor = processor
        self.subscriber = subscriber

        if not hasattr(__class__, "state_metric"):
            __class__.state_metric = Enum(
                'subscriber_state', 'Subscriber state',
                ["processor", "subscriber"],
                states=['stopped', 'running']
            )

        if not hasattr(__class__, "received_metric"):
            __class__.received_metric = Counter(
                'received_count', 'Received count',
                ["processor", "subscriber"],
            )

        if not hasattr(__class__, "dropped_metric"):
            __class__.dropped_metric = Counter(
                'dropped_count', 'Dropped messages count',
                ["processor", "subscriber"],
            )

    def received(self) -> None:
        __class__.received_metric.labels(
            processor=self.processor,
            subscriber=self.subscriber,
        ).inc()

    def state(self, state: str) -> None:
        __class__.state_metric.labels(
            processor=self.processor,
            subscriber=self.subscriber,
        ).state(state)

    def dropped(self, state: str) -> None:
        __class__.dropped_metric.labels(
            processor=self.processor,
            subscriber=self.subscriber,
        ).inc()
