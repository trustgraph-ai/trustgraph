
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
            if msg.type == WSMsgType.ERROR:
                break
            else:
                # Ignore incoming messages
                pass

        running.stop()

    async def async_thread(self, ws, running):

        while running.get():
            try:
                await asyncio.sleep(1)

            except TimeoutError:
                continue

            except Exception as e:
                print(f"Exception: {str(e)}", flush=True)
        
    async def handle(self, request):

        try:
            token = request.query['token']
        except:
            token = ""

        if not self.auth.permitted(token, self.operation):
            return web.HTTPUnauthorized()
        
        running = Running()
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        task = asyncio.create_task(self.async_thread(ws, running))

        try:

            await self.listener(ws, running)

        except Exception as e:
            print(e, flush=True)

        running.stop()

        await ws.close()

        await task

        return ws

    async def start(self):
        pass

    async def join(self):

        # Nothing to wait for
        while True:
            await asyncio.sleep(100)

    def add_routes(self, app):

        app.add_routes([
            web.get(self.path, self.handle),
        ])

