
from . metrics import ConsumerMetrics
from . consumer import Consumer
from . spec import Spec

class ConsumerSpec(Spec):
    def __init__(self, name, schema, handler, concurrency = 1):
        self.name = name
        self.schema = schema
        self.handler = handler
        self.concurrency = concurrency

    def add(self, flow, processor, definition):

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

