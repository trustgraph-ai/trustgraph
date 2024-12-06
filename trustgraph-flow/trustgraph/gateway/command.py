
import asyncio
import queue
from pulsar.schema import JsonSchema
import uuid
from aiohttp import web, WSMsgType

from . socket import SocketEndpoint
from . text_completion import TextCompletionRequestor

class CommandEndpoint(SocketEndpoint):

    def __init__(
            self, pulsar_host, auth,
            services,
            path="/api/v1/command",
    ):

        super(CommandEndpoint, self).__init__(
            endpoint_path=path, auth=auth,
        )

        self.pulsar_host=pulsar_host

#        self.text_completion = TextCompletionRequestor(
#        )

    async def start(self):
        pass

    async def async_thread(self, ws, running):

        id = str(uuid.uuid4())

        while running.get():
            await asyncio.sleep(1)

        running.stop()

    async def listener(self, ws, running):
        
        async for msg in ws:

            # On error, finish
            if msg.type == WSMsgType.ERROR:
                break
            else:

                try:
                    data = msg.json()
                except Exception as e:
                    await ws.send_json({"error": str(e)})
                    continue

                if "service" not in data:
                    await ws.send_json({"error": "Malformed message"})

        running.stop()

