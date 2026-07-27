from __future__ import annotations

from typing import Any

from . spec import Spec

class ProducerSpec(Spec):
    def __init__(self, name: str, schema: Any) -> None:
        self.name = name
        self.schema = schema

    async def register(self, flow: Any, processor: Any, definition: dict[str, Any]) -> Any:

        topic = definition["topics"][self.name]

        handle = await processor.sender_pool.add_producer(
            topic=topic,
            schema=self.schema,
        )

        flow.producer[self.name] = handle
        return handle
