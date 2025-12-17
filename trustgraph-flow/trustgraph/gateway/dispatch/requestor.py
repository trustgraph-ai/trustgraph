
import asyncio
import uuid
import logging

from ... base import Publisher
from ... base import Subscriber

logger = logging.getLogger("requestor")
logger.setLevel(logging.INFO)

class ServiceRequestor:

    def __init__(
            self,
            backend,
            request_queue, request_schema,
            response_queue, response_schema,
            subscription="api-gateway", consumer_name="api-gateway",
            timeout=600,
    ):

        self.pub = Publisher(
            backend, request_queue,
            schema=request_schema,
        )

        self.sub = Subscriber(
            backend, response_queue,
            subscription, consumer_name,
            response_schema
        )

        self.timeout = timeout

        self.running = True

    async def start(self):
        self.running = True
        await self.sub.start()
        await self.pub.start()

    async def stop(self):
        await self.pub.stop()
        await self.sub.stop()
        self.running = False

    def to_request(self, request):
        raise RuntimeError("Not defined")

    def from_response(self, response):
        raise RuntimeError("Not defined")

    async def process(self, request, responder=None):

        id = str(uuid.uuid4())

        try:

            q = await self.sub.subscribe(id)

            await self.pub.send(id, self.to_request(request))

            while self.running:

                try:
                    resp = await asyncio.wait_for(
                        q.get(), timeout=self.timeout
                    )
                except Exception as e:
                    logger.error(f"Request timeout exception: {e}", exc_info=True)
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
            await self.sub.unsubscribe(id)

