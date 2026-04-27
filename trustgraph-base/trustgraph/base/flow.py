
import asyncio

class Flow:
    """
    Runtime representation of a deployed flow process.

    This class maintains internal processor states and orchestrates
    lifecycles (start, stop) for inputs (consumers) and parameters
    that drive data flowing across linked nodes.
    """
    def __init__(self, id, flow, workspace, processor, defn):

        self.id = id
        self.name = flow
        self.workspace = workspace

        self.producer = {}

        # Consumers and publishers.  Is this a bit untidy?
        self.consumer = {}

        self.parameter = {}

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
        if key in self.parameter: return self.parameter[key].value
        return None
