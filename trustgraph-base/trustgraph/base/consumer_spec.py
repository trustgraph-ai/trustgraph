from __future__ import annotations

from typing import Any

from . spec import Spec

class ConsumerSpec(Spec):
    def __init__(self, name: str, schema: Any, handler: Any, concurrency: int = 1) -> None:
        self.name = name
        self.schema = schema
        self.handler = handler
        self.concurrency = concurrency

    async def register(self, flow: Any, processor: Any, definition: dict[str, Any]) -> Any:

        topic = definition["topics"][self.name]
        subscription = (
            processor.id + "--" + flow.workspace + "--" +
            flow.name + "--" + self.name
        )

        handler = self.handler

        async def pool_handler(message):
            await handler(message, None, flow)

        reg = await processor.receiver_pool.add_consumer(
            topic=topic,
            subscription=subscription,
            schema=self.schema,
            handler=pool_handler,
        )

        flow.consumer[self.name] = reg
        return reg

