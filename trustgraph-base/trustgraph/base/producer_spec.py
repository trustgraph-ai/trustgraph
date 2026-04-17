from __future__ import annotations

from typing import Any

from . producer import Producer
from . metrics import ProducerMetrics
from . spec import Spec

class ProducerSpec(Spec):
    def __init__(self, name: str, schema: Any) -> None:
        self.name = name
        self.schema = schema

    def add(self, flow: Any, processor: Any, definition: dict[str, Any]) -> None:

        producer_metrics = ProducerMetrics(
            processor = flow.id, flow = flow.name, name = self.name
        )

        producer = Producer(
            backend = processor.pubsub,
            topic = definition["topics"][self.name],
            schema = self.schema,
            metrics = producer_metrics,
        )

        flow.producer[self.name] = producer
