from __future__ import annotations

from typing import Any

from . metrics import ConsumerMetrics
from . consumer import Consumer
from . spec import Spec

class ConsumerSpec(Spec):
    def __init__(self, name: str, schema: Any, handler: Any, concurrency: int = 1) -> None:
        self.name = name
        self.schema = schema
        self.handler = handler
        self.concurrency = concurrency

    def add(self, flow: Any, processor: Any, definition: dict[str, Any]) -> None:

        consumer_metrics = ConsumerMetrics(
            processor = flow.id, flow = flow.name, name = self.name,
        )

        consumer = Consumer(
            taskgroup = processor.taskgroup,
            flow = flow,
            backend = processor.pubsub,
            topic = definition[self.name],
            subscriber = processor.id + "--" + flow.name + "--" + self.name,
            schema = self.schema,
            handler = self.handler,
            metrics = consumer_metrics,
            concurrency = self.concurrency
        )

        # Consumer handle gets access to producers and other
        # metadata
        consumer.id = flow.id
        consumer.name = self.name
        consumer.flow = flow

        flow.consumer[self.name] = consumer

