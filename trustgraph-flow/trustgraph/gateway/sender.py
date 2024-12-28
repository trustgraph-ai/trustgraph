
# Like ServiceRequestor, but just fire-and-forget instead of request/response

import asyncio
from pulsar.schema import JsonSchema
import uuid
import logging

from . publisher import Publisher

logger = logging.getLogger("sender")
logger.setLevel(logging.INFO)

class ServiceSender:

    def __init__(
            self,
            pulsar_host,
            request_queue, request_schema,
    ):

        self.pub = Publisher(
            pulsar_host, request_queue,
            schema=JsonSchema(request_schema)
        )

    async def start(self):

        self.pub.start()

    def to_request(self, request):
        raise RuntimeError("Not defined")

    async def process(self, request, responder=None):

        try:

            await asyncio.to_thread(
                self.pub.send, None, self.to_request(request)
            )

            return {}

        except Exception as e:

            logging.error(f"Exception: {e}")

            return { "error": str(e) }

