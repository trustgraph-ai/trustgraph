
from . metrics import SubscriberMetrics
from . subscriber import Subscriber
from . spec import Spec

class SubscriberSpec(Spec):

    def __init__(self, name, schema):
        self.name = name
        self.schema = schema

    def add(self, flow, processor, definition):

        subscriber_metrics = SubscriberMetrics(
            processor = flow.id, flow = flow.name, name = self.name
        )

        subscriber = Subscriber(
            client = processor.pulsar_client,
            topic = definition[self.name],
            subscription = flow.id,
            consumer_name = flow.id,
            schema = self.schema,
            metrics = subscriber_metrics,
        )

        # Put it in the consumer map, does that work?
        # It means it gets start/stop call.
        flow.consumer[self.name] = subscriber

