
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

        self.q = asyncio.Queue(maxsize=10)

        self.services = services

    async def start(self):
        pass

    async def ASDasync_thread(self, ws, running):

        while running.get():

            try:
                svc, request = await asyncio.wait_for(self.q.get(), 1)
            except TimeoutError:
                continue
            except Exception as e:
                await ws.send_json({"error": str(e)})

            try:

                print(svc, request)

                requestor = self.services[svc]

                resp = await requestor.process(request)

                await ws.send_json({ "response": resp })

            except Exception as e:

                await ws.send_json({"error": str(e)})

        running.stop()

    async def processor(self, ws, id, service, request):

        try:

            print(id, service, request)

            requestor = self.services[service]

            resp = await requestor.process(request)

            await ws.send_json({"id": id, "response": resp })

        except Exception as e:

            await ws.send_json({"id": id, "error": str(e)})

    async def async_thread(self, ws, running):
        while running.get():
            await asyncio.sleep(1)

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

                    asyncio.create_task(
                        self.processor(
                            ws, data["id"], data["service"], data["request"]
                        )
                    )

                except Exception as e:

                    await ws.send_json({"error": str(e)})
                    continue

        running.stop()

