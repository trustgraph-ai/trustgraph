
import asyncio

class Flow:
    def __init__(self, id, flow, processor, defn):

        self.id = id
        self.name = flow

        self.producer = {}

        # Consumers and publishers.  Is this a bit untidy?
        self.consumer = {}

        self.setting = {}

        for spec in processor.specifications:
            spec.add(self, processor, defn)

    async def start(self):
        for c in self.consumer.values():
            await c.start()

    async def stop(self):
        for c in self.consumer.values():
            await c.stop()

    def __call__(self, key):
        if key in self.producer: return self.producer[key]
        if key in self.consumer: return self.consumer[key]
        if key in self.setting: return self.setting[key].value
        return None
