from __future__ import annotations

from typing import Any

from . metrics import SubscriberMetrics
from . subscriber import Subscriber
from . spec import Spec

class SubscriberSpec(Spec):

    def __init__(self, name: str, schema: Any) -> None:
        self.name = name
        self.schema = schema

    def add(self, flow: Any, processor: Any, definition: dict[str, Any]) -> None:

        subscriber_metrics = SubscriberMetrics(
            processor = flow.id, flow = flow.name, name = self.name
        )

        subscriber = Subscriber(
            backend = processor.pubsub,
            topic = definition["topics"][self.name],
            subscription = flow.id + "--" + flow.workspace + "--" + flow.name,
            consumer_name = flow.id,
            schema = self.schema,
            metrics = subscriber_metrics,
        )

        # Put it in the consumer map, does that work?
        # It means it gets start/stop call.
        flow.consumer[self.name] = subscriber
