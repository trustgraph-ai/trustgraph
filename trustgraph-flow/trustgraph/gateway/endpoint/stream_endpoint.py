
import asyncio
from aiohttp import web
import logging

logger = logging.getLogger("endpoint")
logger.setLevel(logging.INFO)

class StreamEndpoint:

    def __init__(self, endpoint_path, auth, dispatcher):

        self.path = endpoint_path

        self.auth = auth
        self.operation = "service"

        self.dispatcher = dispatcher

    async def start(self):
        pass

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

            data = request.content

            async def error(err):
                return web.HTTPInternalServerError(text = err)

            async def ok(
                    status=200, reason="OK", type="application/octet-stream"
            ):
                response = web.StreamResponse(
                    status = status, reason = reason,
                    headers = {"Content-Type": type}
                )
                await response.prepare(request)
                return response

            resp = await self.dispatcher.process(
                data, error, ok, request
            )

            return resp

        except Exception as e:
            logging.error(f"Exception: {e}")

            return web.json_response(
                { "error": str(e) }
            )

