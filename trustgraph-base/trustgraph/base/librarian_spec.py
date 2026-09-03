from __future__ import annotations

import uuid
from typing import Any

from . spec import Spec, TimeoutSpec
from . async_librarian_client import AsyncLibrarianClient, default_librarian_timeout


class LibrarianSpec(TimeoutSpec, Spec):

    timeout_param = "librarian_timeout"
    default_timeout = default_librarian_timeout

    def __init__(self, request_name="librarian-request",
                 response_name="librarian-response", timeout=None):
        self.request_name = request_name
        self.response_name = response_name
        self.timeout = timeout

    async def register(self, flow: Any, processor: Any, definition: dict[str, Any]) -> Any:

        subscription = (
            processor.id + "--" + flow.workspace + "--" +
            flow.name + "--librarian--" + str(uuid.uuid4())
        )

        client = await AsyncLibrarianClient.create(
            backend=processor.async_backend,
            request_topic=definition["topics"][self.request_name],
            response_topic=definition["topics"][self.response_name],
            subscription=subscription,
            default_timeout=self.resolve_timeout(processor),
        )

        flow.librarian = client
        return client
