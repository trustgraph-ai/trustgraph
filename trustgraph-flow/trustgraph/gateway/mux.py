
import asyncio
import queue
import uuid
from aiohttp import web, WSMsgType

from . socket import SocketEndpoint

MAX_OUTSTANDING_REQUESTS = 15
WORKER_CLOSE_WAIT = 0.01
START_REQUEST_WAIT = 0.1

# This buffers requests until task start, so short-lived
MAX_QUEUE_SIZE = 10

class MuxEndpoint(SocketEndpoint):

    def __init__(
            self, pulsar_client, auth,
            services,
            path="/api/v1/socket",
    ):

        super(MuxEndpoint, self).__init__(
            endpoint_path=path, auth=auth,
        )

        self.services = services

    async def start(self):
        pass

    async def maybe_tidy_workers(self, workers):

        while True:

            try:

                await asyncio.wait_for(
                    asyncio.shield(workers[0]),
                    WORKER_CLOSE_WAIT
                )

                # worker[0] now stopped
                # FIXME: Delete reference???

                workers.pop(0)

                if len(workers) == 0:
                    break

                # Loop iterates to try the next worker

            except TimeoutError:
                # worker[0] still running, move on
                break

    async def start_request_task(self, ws, id, svc, request, workers):

        if svc not in self.services:
            await ws.send_json({"id": id, "error": "Service not recognised"})
            return
            
        requestor = self.services[svc]

        async def responder(resp, fin):
            await ws.send_json({
                "id": id,
                "response": resp,
                "complete": fin,
            })

        # Wait for outstanding requests to go below MAX_OUTSTANDING_REQUESTS
        while len(workers) > MAX_OUTSTANDING_REQUESTS:

            # Fixes deadlock
            # FIXME: Put it in its own loop
            await asyncio.sleep(START_REQUEST_WAIT)

            await self.maybe_tidy_workers(workers)

        worker = asyncio.create_task(
            requestor.process(request, responder)
        )

        workers.append(worker)

    async def async_thread(self, ws, running, q):

        # Worker threads, servicing
        workers = []

        while running.get():

            try:

                if len(workers) > 0:
                    await self.maybe_tidy_workers(workers)

                # Get next request on queue
                id, svc, request = await asyncio.wait_for(q.get(), 1)

            except TimeoutError:
                continue

            except Exception as e:
                # This is an internal working error, may not be recoverable
                print("Exception:", e)
                await ws.send_json({"id": id, "error": str(e)})
                break

            try:
                print(id, svc, request)
                await self.start_request_task(ws, id, svc, request, workers)

            except Exception as e:
                print("Exception2:", e)
                await ws.send_json({"error": str(e)})

        running.stop()

    async def listener(self, ws, running):

        # The outstanding request queue, max size is MAX_QUEUE_SIZE
        q = asyncio.Queue(maxsize=MAX_QUEUE_SIZE)

        async_task = asyncio.create_task(self.async_thread(
            ws, running, q
        ))
        
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

                    await q.put(
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

        await async_task
