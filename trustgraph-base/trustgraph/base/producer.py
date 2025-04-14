
class Producer:

    def __init__(self, client, queue, schema):
        self.client = client
        self.queue = queue
        self.schema = schema

        self.producer = None

    async def send(self, msg, properties={}):

        if self.producer == None:
            self.producer = self.client.publish(self.queue, self.schema)
        

        self.producer.send(msg, properties)

        # FIXME
#         __class__.output_metric.inc()

