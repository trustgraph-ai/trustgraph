
from . metrics import ConsumerMetrics
from . consumer import Consumer
from . spec import Spec

class ConsumerSpec(Spec):
    def __init__(self, name, schema, handler):
        self.name = name
        self.schema = schema
        self.handler = handler

    def add(self, flow, processor, definition):

        consumer_metrics = ConsumerMetrics(
            flow.id, f"{flow.name}-{self.name}"
        )

        consumer = Consumer(
            taskgroup = processor.taskgroup,
            flow = flow,
            client = processor.client,
            topic = definition[self.name],
            subscriber = flow.id,
            schema = self.schema,
            handler = self.handler,
            metrics = consumer_metrics,
        )

        # Consumer handle gets access to producers and other
        # metadata
        consumer.id = flow.id
        consumer.name = self.name
        consumer.flow = flow

        flow.consumer[self.name] = consumer

