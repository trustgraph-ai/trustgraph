
import asyncio
import queue
from pulsar.schema import JsonSchema
import uuid
from aiohttp import web, WSMsgType

from . socket import SocketEndpoint
from . text_completion import TextCompletionRequestor

class MuxEndpoint(SocketEndpoint):

    def __init__(
            self, pulsar_host, auth,
            services,
            path="/api/v1/socket",
    ):

        super(MuxEndpoint, self).__init__(
            endpoint_path=path, auth=auth,
        )

        self.q = asyncio.Queue(maxsize=10)

        self.services = services

    async def start(self):
        pass

    async def async_thread(self, ws, running):

        while running.get():

            try:
                id, svc, request = await asyncio.wait_for(self.q.get(), 1)
            except TimeoutError:
                continue
            except Exception as e:
                await ws.send_json({"id": id, "error": str(e)})

            try:

                print(svc, request)

                requestor = self.services[svc]

                async def responder(resp, fin):
                    await ws.send_json({
                        "id": id,
                        "response": resp,
                        "complete": fin,
                    })

                resp = await requestor.process(request, responder)

            except Exception as e:

                await ws.send_json({"error": str(e)})

        running.stop()

    async def listener(self, ws, running):
        
        async for msg in ws:

            # On error, finish
            if msg.type == WSMsgType.ERROR:
                break
            else:

                try:

                    data = msg.json()

                    if data["service"] not in self.services:
                        raise RuntimeError("Bad service")

                    if "request" not in data:
                        raise RuntimeError("Bad message")

                    if "id" not in data:
                        raise RuntimeError("Bad message")

                    await self.q.put(
                        (data["id"], data["service"], data["request"])
                    )

                except Exception as e:

                    await ws.send_json({"error": str(e)})
                    continue

        running.stop()

