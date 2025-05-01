
import asyncio
from aiohttp import web, WSMsgType
import logging

from .. running import Running

logger = logging.getLogger("socket")
logger.setLevel(logging.INFO)

class SocketEndpoint:

    def __init__(
            self, endpoint_path, auth,
    ):

        self.path = endpoint_path
        self.auth = auth
        self.operation = "socket"

        self.running = Running()

    async def dispatcher(self, ws):
        pass

    async def listener(self, ws):

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

        self.running.stop()
        await ws.close()
        
    async def handle(self, request):

        try:
            token = request.query['token']
        except:
            token = ""

        if not self.auth.permitted(token, self.operation):
            return web.HTTPUnauthorized()
        
        # 50MB max message size
        ws = web.WebSocketResponse(max_msg_size=52428800)

        await ws.prepare(request)

        try:

            async with asyncio.TaskGroup() as tg:
            
                worker = tg.create_task(
                    self.dispatcher(ws)
                )

                worker = tg.create_task(
                    self.listener(ws)
                )

                # Wait for threads to complete

        except Exception as e:
            print("Socket exception:", e, flush=True)

        await ws.close()

        return ws

    async def start(self):
        pass

    async def stop(self):
        self.running.stop()

    def add_routes(self, app):

        app.add_routes([
            web.get(self.path, self.handle),
        ])

