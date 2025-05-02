
import asyncio
from aiohttp import web, WSMsgType
import logging

from .. running import Running

logger = logging.getLogger("socket")
logger.setLevel(logging.INFO)

class SocketEndpoint:

    def __init__(
            self, endpoint_path, auth, dispatcher,
    ):

        self.path = endpoint_path
        self.auth = auth
        self.operation = "socket"

        self.dispatcher = dispatcher

    async def worker(self, ws, dispatcher, running):

        await dispatcher.run()

    async def listener(self, ws, dispatcher, running):

        async for msg in ws:

            # On error, finish
            if msg.type == WSMsgType.TEXT:
                await dispatcher.receive(msg)
                continue
            elif msg.type == WSMsgType.BINARY:
                await dispatcher.receive(msg)
                continue
            else:
                break

        running.stop()
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

                running = Running()

                dispatcher = await self.dispatcher(
                    ws, running, request.match_info
                )

                worker_task = tg.create_task(
                    self.worker(ws, dispatcher, running)
                )

                lsnr_task = tg.create_task(
                    self.listener(ws, dispatcher, running)
                )

                print("Created taskgroup, waiting...")

                # Wait for threads to complete

            print("Task group closed")

            # Finally?
            await dispatcher.destroy()

        except ExceptionGroup as e:

            print("Exception group:", flush=True)

            for se in e.exceptions:
                print("  Type:", type(se), flush=True)
                print(f"  Exception: {se}", flush=True)
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

