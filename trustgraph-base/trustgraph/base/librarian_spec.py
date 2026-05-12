from __future__ import annotations

import uuid
from typing import Any

from . spec import Spec
from . librarian_client import LibrarianClient


class LibrarianSpec(Spec):
    def __init__(self, request_name="librarian-request",
                 response_name="librarian-response"):
        self.request_name = request_name
        self.response_name = response_name

    def add(self, flow: Any, processor: Any, definition: dict[str, Any]) -> None:

        client = LibrarianClient(
            id=flow.id,
            backend=processor.pubsub,
            taskgroup=processor.taskgroup,
            librarian_request_queue=definition["topics"][self.request_name],
            librarian_response_queue=definition["topics"][self.response_name],
            librarian_subscriber=(
                processor.id + "--" + flow.workspace + "--" +
                flow.name + "--librarian--" + str(uuid.uuid4())
            ),
            flow_name=flow.name,
        )

        flow.librarian = client
