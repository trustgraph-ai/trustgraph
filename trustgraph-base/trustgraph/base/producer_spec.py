
from . producer import Producer
from . metrics import ProducerMetrics
from . spec import Spec

class ProducerSpec(Spec):
    def __init__(self, name, schema):
        self.name = name
        self.schema = schema

    def add(self, flow, processor, definition):

        producer_metrics = ProducerMetrics(
            flow.id, f"{flow.name}-{self.name}"
        )

        producer = Producer(
            client = processor.client,
            topic = definition[self.name],
            schema = self.schema,
            metrics = producer_metrics,
        )

        flow.producer[self.name] = producer

