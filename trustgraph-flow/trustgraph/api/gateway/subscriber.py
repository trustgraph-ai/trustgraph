
import asyncio

class Subscriber:

    def __init__(self, pulsar_host, topic, subscription, consumer_name,
                 schema=None, max_size=10):
        self.pulsar_host = pulsar_host
        self.topic = topic
        self.subscription = subscription
        self.consumer_name = consumer_name
        self.schema = schema
        self.q = {}
        self.full = {}

    async def run(self, client):
        while True:
            try:
                async with client.subscribe(
                    topic=self.topic,
                    subscription_name=self.subscription,
                    consumer_name=self.consumer_name,
                    schema=self.schema,
                ) as consumer:
                    while True:
                        msg = await consumer.receive()

                        # Acknowledge successful reception of the message
                        await consumer.acknowledge(msg)

                        try:
                            id = msg.properties()["id"]
                        except:
                            id = None

                        value = msg.value()
                        if id in self.q:
                            await self.q[id].put(value)

                        for q in self.full.values():
                            await q.put(value)

            except Exception as e:
                print("Exception:", e, flush=True)
         
            # If handler drops out, sleep a retry
            await asyncio.sleep(2)

    async def subscribe(self, id):
        q = asyncio.Queue()
        self.q[id] = q
        return q

    async def unsubscribe(self, id):
        if id in self.q:
            del self.q[id]
    
    async def subscribe_all(self, id):
        q = asyncio.Queue()
        self.full[id] = q
        return q

    async def unsubscribe_all(self, id):
        if id in self.full:
            del self.full[id]

