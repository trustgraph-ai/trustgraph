
import asyncio
from aiohttp import web, WSMsgType
import logging

from . running import Running

logger = logging.getLogger("socket")
logger.setLevel(logging.INFO)

class SocketEndpoint:

    def __init__(
            self,
            endpoint_path="/api/v1/socket",
    ):

        self.path = endpoint_path

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

        running = Running()
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        task = asyncio.create_task(self.async_thread(ws, running))

        await self.listener(ws, running)

        await task

        running.stop()

        return ws

    async def start(self):
        pass

    def add_routes(self, app):

        app.add_routes([
            web.get(self.path, self.handle),
        ])

