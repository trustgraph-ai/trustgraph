import asyncio
import logging

from ... schema import Metadata
from ... schema import ExtractedObject

logger = logging.getLogger(__name__)

class RowsImport:

    def __init__(self, ws, running, backend, queue):
        self.ws = ws
        self.running = running
        self.backend = backend
        self.queue = queue
        self.producer = None

    async def start(self):
        self.producer = await self.backend.create_producer(
            topic=self.queue, schema=ExtractedObject,
        )

    async def destroy(self):
        self.running.stop()
        if self.producer:
            await self.producer.close()
            self.producer = None
        if self.ws:
            await self.ws.close()

    async def receive(self, msg):
        data = msg.json()

        values_data = data["values"]
        if not isinstance(values_data, list):
            values_data = [values_data]

        elt = ExtractedObject(
            metadata=Metadata(
                id=data["metadata"]["id"],
                collection=data["metadata"]["collection"],
            ),
            schema_name=data["schema_name"],
            values=values_data,
            confidence=data.get("confidence", 1.0),
            source_span=data.get("source_span", ""),
        )

        await self.producer.send(elt)

    async def run(self):
        while self.running.get():
            await asyncio.sleep(0.5)

        if self.ws:
            await self.ws.close()
        self.ws = None
