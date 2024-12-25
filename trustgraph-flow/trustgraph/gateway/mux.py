
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

        # The outstanding request queue, max size is 10
        self.q = asyncio.Queue(maxsize=10)

        # Worker threads, servicing
        self.workers = []

        self.services = services

    async def start(self):
        pass

    async def maybe_tidy_workers(self):

        while True:
            try:

                await asyncio.wait_for(
                    asyncio.shield(self.workers[0]),
                    0.05
                )

                # worker[0] now stopped
                self.workers = self.workers[1:]

                if len(self.workers) == 0:
                    break

                # Loop iterates to try the next worker

            except TimeoutError:
                # worker[0] still running, move on
                break

    async def start_request_task(self, ws, id, svc, request):

        requestor = self.services[svc]

        async def responder(resp, fin):
            print("respnd", id)
            print(svc, request)
            await ws.send_json({
                "id": id,
                "response": resp,
                "complete": fin,
            })

        # Wait for outstanding requests to go below 15
        while len(self.workers) > 15:
            await asyncio.sleep(0.1)

        worker = asyncio.create_task(
            requestor.process(request, responder)
        )

        self.workers.append(worker)

    async def async_thread(self, ws, running):

        while running.get():

            try:

                if len(self.workers) > 0:
                    await self.maybe_tidy_workers()

                # Get next request on queue
                id, svc, request = await asyncio.wait_for(self.q.get(), 1)

            except TimeoutError:
                continue

            except Exception as e:
                # This is an internal working error, may not be recoverable
                print("Exception:", e)
                await ws.send_json({"id": id, "error": str(e)})
                break

            try:
                print(id, svc, request)
                await self.start_request_task(ws, id, svc, request)

            except Exception as e:
                print("Exception2:", e)
                await ws.send_json({"error": str(e)})

        running.stop()

    async def listener(self, ws, running):
        
        async for msg in ws:

            # On error, finish
            if msg.type == WSMsgType.TEXT:

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

            elif msg.type == WSMsgType.ERROR:
                break
            elif msg.type == WSMsgType.CLOSE:
                break
            else:
                break

        running.stop()

