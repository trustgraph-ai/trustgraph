
import logging

from aiohttp import web

from .. capabilities import enforce, enforce_workspace

logger = logging.getLogger("endpoint")
logger.setLevel(logging.INFO)


class ConstantEndpoint:

    def __init__(self, endpoint_path, auth, dispatcher, capability):

        self.path = endpoint_path
        self.auth = auth
        self.capability = capability
        self.dispatcher = dispatcher

    async def start(self):
        pass

    def add_routes(self, app):
        app.add_routes([
            web.post(self.path, self.handle),
        ])

    async def handle(self, request):

        logger.debug(f"Processing request: {request.path}")

        identity = await enforce(request, self.auth, self.capability)

        try:
            data = await request.json()

            if identity is not None:
                await enforce_workspace(data, identity, self.auth)

            async def responder(x, fin):
                pass

            resp = await self.dispatcher.process(data, responder)

            return web.json_response(resp)

        except web.HTTPException:
            raise
        except Exception as e:
            logger.error(f"Exception: {e}", exc_info=True)
            return web.json_response({"error": str(e)})
