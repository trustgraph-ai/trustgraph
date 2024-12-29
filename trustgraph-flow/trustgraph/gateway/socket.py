
import asyncio
from aiohttp import web, WSMsgType
import logging

from . running import Running

logger = logging.getLogger("socket")
logger.setLevel(logging.INFO)

class SocketEndpoint:

    def __init__(
            self, endpoint_path, auth,
    ):

        self.path = endpoint_path
        self.auth = auth
        self.operation = "socket"

    async def listener(self, ws, running):
        
        async for msg in ws:
            # On error, finish
            if msg.type == WSMsgType.TEXT:
                # Ignore incoming message
                continue
            elif msg.type == WSMsgType.BINARY:
                # Ignore incoming message
                continue
            else:
                break

        running.stop()
        
    async def handle(self, request):

        try:
            token = request.query['token']
        except:
            token = ""

        if not self.auth.permitted(token, self.operation):
            return web.HTTPUnauthorized()
        
        running = Running()

        # 50MB max message size
        ws = web.WebSocketResponse(max_msg_size=52428800)

        await ws.prepare(request)

        try:
            await self.listener(ws, running)
        except Exception as e:
            print(e, flush=True)

        running.stop()

        await ws.close()

        return ws

    async def start(self):
        pass

    def add_routes(self, app):

        app.add_routes([
            web.get(self.path, self.handle),
        ])

