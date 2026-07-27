from __future__ import annotations

import uuid
from typing import Any

from . spec import Spec


class LibrarianSpec(Spec):
    def __init__(self, request_name="librarian-request",
                 response_name="librarian-response"):
        self.request_name = request_name
        self.response_name = response_name

    async def register(self, flow: Any, processor: Any, definition: dict[str, Any]) -> Any:

        from .async_librarian_client import AsyncLibrarianClient

        subscription = (
            processor.id + "--" + flow.workspace + "--" +
            flow.name + "--librarian--" + str(uuid.uuid4())
        )

        client = await AsyncLibrarianClient.create(
            backend=processor.async_backend,
            request_topic=definition["topics"][self.request_name],
            response_topic=definition["topics"][self.response_name],
            subscription=subscription,
        )

        flow.librarian = client
        return client
