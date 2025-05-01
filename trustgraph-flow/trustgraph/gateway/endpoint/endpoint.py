
import asyncio
from aiohttp import web
import uuid
import logging

logger = logging.getLogger("endpoint")
logger.setLevel(logging.INFO)

class ServiceEndpoint:

    def __init__(self, endpoint_path, auth, requestor):

        self.path = endpoint_path

        self.auth = auth
        self.operation = "service"

        self.requestor = requestor

    async def start(self):
        await self.requestor.start()

    def add_routes(self, app):

        app.add_routes([
            web.post(self.path, self.handle),
        ])

    async def handle(self, request):

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

            async def responder(x, fin):
                print(x)

            resp = await self.requestor.process(data, responder)

            return web.json_response(resp)

        except Exception as e:
            logging.error(f"Exception: {e}")

            return web.json_response(
                { "error": str(e) }
            )

