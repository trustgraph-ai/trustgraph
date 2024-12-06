
import asyncio
from pulsar.schema import JsonSchema
import uuid
import logging

from . publisher import Publisher
from . subscriber import Subscriber

logger = logging.getLogger("requestor")
logger.setLevel(logging.INFO)

class ServiceRequestor:

    def __init__(
            self,
            pulsar_host,
            request_queue, request_schema,
            response_queue, response_schema,
            subscription="api-gateway", consumer_name="api-gateway",
            timeout=600,
    ):

        self.pub = Publisher(
            pulsar_host, request_queue,
            schema=JsonSchema(request_schema)
        )

        self.sub = Subscriber(
            pulsar_host, response_queue,
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

    async def process(self, request):

        id = str(uuid.uuid4())

        try:

            q = self.sub.subscribe(id)

            await asyncio.to_thread(
                self.pub.send, id, self.to_request(request)
            )

            try:
                resp = await asyncio.to_thread(q.get, timeout=self.timeout)
            except Exception as e:
                raise RuntimeError("Timeout")

            if resp.error:
                return { "error": resp.error.message }

            return self.from_response(resp)

        except Exception as e:

            logging.error(f"Exception: {e}")

            return { "error": str(e) }

        finally:
            self.sub.unsubscribe(id)

class MultiResponseServiceRequestor(ServiceRequestor):

    async def process(self, request, responder):

        id = str(uuid.uuid4())

        try:

            q = self.sub.subscribe(id)

            await asyncio.to_thread(
                self.pub.send, id, self.to_request(request)
            )

            # Keeps looking at responses...

            while True:

                try:
                    resp = await asyncio.to_thread(q.get, timeout=self.timeout)
                except Exception as e:
                    raise RuntimeError("Timeout")

                if resp.error:
                    return { "error": resp.error.message }

                # Until from_response says we have a finished answer
                resp, fin = self.from_response(resp)

                responder(resp)

                if fin:
                    return resp

                # Not finished, so loop round and continue

        except Exception as e:

            logging.error(f"Exception: {e}")

            return { "error": str(e) }

        finally:
            self.sub.unsubscribe(id)

