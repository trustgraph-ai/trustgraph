
import asyncio
from pulsar.schema import JsonSchema
from aiohttp import web
import uuid
import logging

from . publisher import Publisher
from . subscriber import Subscriber

logger = logging.getLogger("endpoint")
logger.setLevel(logging.INFO)

class ServiceEndpoint:

    def __init__(
            self,
            pulsar_host,
            request_queue, request_schema,
            response_queue, response_schema,
            endpoint_path,
            auth,
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

        self.path = endpoint_path
        self.timeout = timeout
        self.auth = auth

        self.operation = "service"

    async def start(self):

        self.pub.start()
        self.sub.start()

    def add_routes(self, app):

        app.add_routes([
            web.post(self.path, self.handle),
        ])

    def to_request(self, request):
        raise RuntimeError("Not defined")

    def from_response(self, response):
        raise RuntimeError("Not defined")

    async def handle(self, request):

        id = str(uuid.uuid4())

        print(request.path, "...")

        try:
            ht = request.headers["Authorization"]
            tokens = ht.split(" ", 2)
            if tokens[0] != "Bearer":
                return web.HTTPUnauthorized()
            token = tokens[1]
        except:
            token = ""

        if not self.auth.permitted(token, self.operation):
            return web.HTTPUnauthorized()

        try:

            data = await request.json()

            print(data)

            q = self.sub.subscribe(id)

            await asyncio.to_thread(
                self.pub.send, id, self.to_request(data)
            )

            try:
                resp = await asyncio.to_thread(q.get, timeout=self.timeout)
            except Exception as e:
                raise RuntimeError("Timeout")

            if resp.error:
                print("Error")
                return web.json_response(
                    { "error": resp.error.message }
                )

            return web.json_response(
                self.from_response(resp)
            )

        except Exception as e:
            logging.error(f"Exception: {e}")

            return web.json_response(
                { "error": str(e) }
            )

        finally:
            self.sub.unsubscribe(id)


class MultiResponseServiceEndpoint(ServiceEndpoint):

    async def handle(self, request):

        id = str(uuid.uuid4())

        try:

            data = await request.json()

            q = self.sub.subscribe(id)

            await asyncio.to_thread(
                self.pub.send, id, self.to_request(data)
            )

            # Keeps looking at responses...

            while True:

                try:
                    resp = await asyncio.to_thread(q.get, timeout=self.timeout)
                except Exception as e:
                    raise RuntimeError("Timeout waiting for response")

                if resp.error:
                    return web.json_response(
                        { "error": resp.error.message }
                    )

                # Until from_response says we have a finished answer
                resp, fin = self.from_response(resp)


                if fin:
                    return web.json_response(resp)

                # Not finished, so loop round and continue

        except Exception as e:
            logging.error(f"Exception: {e}")

            return web.json_response(
                { "error": str(e) }
            )

        finally:
            self.sub.unsubscribe(id)
