
from . producer import Producer
from . metrics import ProducerMetrics
from . spec import Spec

class ProducerSpec(Spec):
    def __init__(self, name, schema):
        self.name = name
        self.schema = schema

    def add(self, flow, processor, definition):

        producer_metrics = ProducerMetrics(
            processor = flow.id, flow = flow.name, name = self.name
        )

        producer = Producer(
            backend = processor.pubsub,
            topic = definition[self.name],
            schema = self.schema,
            metrics = producer_metrics,
        )

        flow.producer[self.name] = producer

