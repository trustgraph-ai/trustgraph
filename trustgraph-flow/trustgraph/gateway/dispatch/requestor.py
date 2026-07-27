
import asyncio
import logging

from ... base.request_response_client import RequestResponseClient

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

        self.backend = backend
        self.request_queue = request_queue
        self.request_schema = request_schema
        self.response_queue = response_queue
        self.response_schema = response_schema
        self.timeout = timeout
        self.client = None
        self.running = True

    async def start(self):
        self.running = True
        self.client = await RequestResponseClient.create(
            backend=self.backend,
            request_topic=self.request_queue,
            response_topic=self.response_queue,
            request_schema=self.request_schema,
            response_schema=self.response_schema,
        )

    async def stop(self):
        self.running = False
        if self.client:
            await self.client.close()
            self.client = None

    def to_request(self, request):
        raise RuntimeError("Not defined")

    def from_response(self, response):
        raise RuntimeError("Not defined")

    async def process(self, request, responder=None):

        try:

            if responder is None:
                resp = await self.client.request(
                    self.to_request(request),
                    timeout=self.timeout,
                )

                if resp.error:
                    return { "error": {
                        "type": resp.error.type,
                        "message": resp.error.message,
                    } }

                result, fin = self.from_response(resp)
                return result

            async for resp in self.client.request_stream(
                self.to_request(request),
                timeout=self.timeout,
            ):

                if resp.error:
                    err = { "error": {
                        "type": resp.error.type,
                        "message": resp.error.message,
                    } }
                    await responder(err, True)
                    return err

                result, fin = self.from_response(resp)
                await responder(result, fin)

                if fin:
                    return result

        except Exception as e:

            logging.error(f"Exception: {e}")

            err = { "error": {
                "type": "gateway-error",
                "message": str(e),
            } }
            if responder:
                await responder(err, True)
            return err

