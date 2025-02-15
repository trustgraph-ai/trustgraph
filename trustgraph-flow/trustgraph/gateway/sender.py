
# Like ServiceRequestor, but just fire-and-forget instead of request/response

import asyncio
from pulsar.schema import JsonSchema
import uuid
import logging

from .. base import Publisher

logger = logging.getLogger("sender")
logger.setLevel(logging.INFO)

class ServiceSender:

    def __init__(
            self,
            pulsar_client,
            request_queue, request_schema,
            pulsar_api_key=None,
    ):

        self.pub = Publisher(
            pulsar_client, request_queue,
            schema=JsonSchema(request_schema),
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

            if responder:
                await responder({}, True)

        except Exception as e:

            logging.error(f"Exception: {e}")

            err = { "error": str(e) }

            if responder:
                await responder(err, True)

            return err

