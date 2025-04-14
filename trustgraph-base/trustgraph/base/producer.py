
class Producer:

    def __init__(self, client, queue, schema, metrics=None):
        self.client = client
        self.queue = queue
        self.schema = schema

        self.producer = self.client.publish(self.queue, self.schema)

        self.metrics = metrics

    async def send(self, msg, properties={}):

        if self.metrics:
            self.metrics.inc()

        self.producer.send(msg, properties)

        # FIXME
#         __class__.output_metric.inc()

