
import asyncio
from aiohttp import web, WSMsgType
import logging

from .. running import Running
from . socket import SocketEndpoint

logger = logging.getLogger("socket")
logger.setLevel(logging.INFO)

class StreamEndpoint(SocketEndpoint):

    def __init__(
            self, endpoint_path, auth, dispatchers,
    ):

        super(StreamEndpoint, self).__init__(endpoint_path, auth)

    async def listener(self, ws):

        async for msg in ws:
            # On error, finish
            if msg.type == WSMsgType.TEXT:
                print("Received:", msg)
                continue
            elif msg.type == WSMsgType.BINARY:
                # Ignore incoming message
                continue
            else:
                break

        self.running.stop()
        
    async def dispatcher(self, ws):

        for i in range(0, 10):

            await asyncio.sleep(1)

            await ws.send_json({"number": i})

        await ws.close()
        self.running.stop()

