
import asyncio
from pulsar.schema import JsonSchema
import uuid
import logging

from .. base import Publisher
from .. base import Subscriber

logger = logging.getLogger("requestor")
logger.setLevel(logging.INFO)

class ServiceRequestor:

    def __init__(
            self,
            pulsar_client,
            request_queue, request_schema,
            response_queue, response_schema,
            subscription="api-gateway", consumer_name="api-gateway",
            timeout=600,
    ):

        self.pub = Publisher(
            pulsar_client, request_queue,
            schema=JsonSchema(request_schema),
        )

        self.sub = Subscriber(
            pulsar_client, response_queue,
            subscription, consumer_name,
            JsonSchema(response_schema)
        )

        self.timeout = timeout

    async def start(self):

        self.pub.start()
        self.sub.start()

    def to_request(self, request):
        raise RuntimeError("Not defined")

    def from_response(self, response):
        raise RuntimeError("Not defined")

    async def process(self, request, responder=None):

        id = str(uuid.uuid4())

        try:

            q = self.sub.subscribe(id)

            await asyncio.to_thread(
                self.pub.send, id, self.to_request(request)
            )

            while True:

                try:
                    resp = await asyncio.to_thread(
                        q.get,
                        timeout=self.timeout
                    )
                except Exception as e:
                    raise RuntimeError("Timeout")

                if resp.error:
                    err = { "error": {
                        "type": resp.error.type,
                        "message": resp.error.message,
                    } }
                    if responder:
                        await responder(err, True)
                    return err

                resp, fin = self.from_response(resp)

                print(resp, fin)

                if responder:
                    await responder(resp, fin)

                if fin:
                    return resp

        except Exception as e:

            logging.error(f"Exception: {e}")

            err = { "error": {
                "type": "gateway-error",
                "message": str(e),
            } }
            if responder:
                await responder(err, True)
            return err

        finally:
            self.sub.unsubscribe(id)

