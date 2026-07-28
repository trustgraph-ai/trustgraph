from __future__ import annotations

import time
from typing import Any

from prometheus_client import start_http_server, Info, Enum, Histogram
from prometheus_client import Counter, Gauge

BUCKETS_STANDARD = (
    0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0,
)

BUCKETS_LLM = (
    0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0,
)

BUCKETS_SESSION = (
    1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0,
)


class ConsumerMetrics:

    def __init__(self, processor: str, consumer: str) -> None:

        self.processor = processor
        self.consumer = consumer

        if not hasattr(__class__, "state_metric"):
            __class__.state_metric = Enum(
                'tg_consumer_state', 'Consumer state',
                ["processor", "consumer"],
                states=['stopped', 'running']
            )

        if not hasattr(__class__, "request_metric"):
            __class__.request_metric = Histogram(
                'tg_consumer_request_duration_seconds',
                'Request latency (seconds)',
                ["processor", "consumer"],
                buckets=BUCKETS_STANDARD,
            )

        if not hasattr(__class__, "processing_metric"):
            __class__.processing_metric = Counter(
                'tg_consumer_processing_total', 'Processing count',
                ["processor", "consumer", "status"],
            )

        if not hasattr(__class__, "rate_limit_metric"):
            __class__.rate_limit_metric = Counter(
                'tg_consumer_rate_limit_total',
                'Rate limit event count',
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

    def observe_latency(self, duration: float) -> None:
        __class__.request_metric.labels(
            processor=self.processor, consumer=self.consumer,
        ).observe(duration)


class ProducerMetrics:

    def __init__(self, processor: str, producer: str) -> None:

        self.processor = processor
        self.producer = producer

        if not hasattr(__class__, "producer_metric"):
            __class__.producer_metric = Counter(
                'tg_producer_messages_total',
                'Output items produced',
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


class DownstreamMetrics:

    def __init__(self, processor: str, target_service: str) -> None:

        self.processor = processor
        self.target_service = target_service

        if not hasattr(__class__, "duration_metric"):
            __class__.duration_metric = Histogram(
                'tg_downstream_call_duration_seconds',
                'Downstream request/response call latency (seconds)',
                ["processor", "target_service"],
                buckets=BUCKETS_STANDARD,
            )

        if not hasattr(__class__, "timeout_metric"):
            __class__.timeout_metric = Counter(
                'tg_downstream_timeout_total',
                'Downstream call timeout count',
                ["processor", "target_service"],
            )

        if not hasattr(__class__, "error_metric"):
            __class__.error_metric = Counter(
                'tg_downstream_error_total',
                'Downstream call error count',
                ["processor", "target_service", "error_type"],
            )

        __class__.duration_metric.labels(
            processor=self.processor, target_service=self.target_service,
        )
        __class__.timeout_metric.labels(
            processor=self.processor, target_service=self.target_service,
        )

    def observe_duration(self, duration: float) -> None:
        __class__.duration_metric.labels(
            processor=self.processor,
            target_service=self.target_service,
        ).observe(duration)

    def timeout(self) -> None:
        __class__.timeout_metric.labels(
            processor=self.processor,
            target_service=self.target_service,
        ).inc()

    def error(self, error_type: str) -> None:
        __class__.error_metric.labels(
            processor=self.processor,
            target_service=self.target_service,
            error_type=error_type,
        ).inc()


class ProcessorMetrics:
    def __init__(self, processor: str) -> None:

        self.processor = processor

        if not hasattr(__class__, "processor_metric"):
            __class__.processor_metric = Info(
                'tg_processor', 'Processor configuration',
                ["processor"]
            )

        if not hasattr(__class__, "config_version_metric"):
            __class__.config_version_metric = Gauge(
                'tg_config_version',
                'Current config version known to this processor',
                ["processor"],
            )

    def info(self, info: dict[str, str]) -> None:
        __class__.processor_metric.labels(
            processor=self.processor
        ).info(info)

    def set_config_version(self, version: int) -> None:
        __class__.config_version_metric.labels(
            processor=self.processor
        ).set(version)
