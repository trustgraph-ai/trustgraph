
import asyncio
import queue
import uuid

MAX_OUTSTANDING_REQUESTS = 15
WORKER_CLOSE_WAIT = 0.01
START_REQUEST_WAIT = 0.1

# This buffers requests until task start, so short-lived
MAX_QUEUE_SIZE = 10

class Mux:

    def __init__(self, dispatcher_manager, ws, running):

        self.dispatcher_manager = dispatcher_manager
        self.ws = ws
        self.running = running

        self.q = asyncio.Queue(maxsize=MAX_QUEUE_SIZE)

    async def destroy(self):

        self.running.stop()

        if self.ws:
            await self.ws.close()

    async def receive(self, msg):

        try:

            data = msg.json()

#            if data["service"] not in self.services:
#                raise RuntimeError("Bad service")

            if "request" not in data:
                raise RuntimeError("Bad message")

            if "id" not in data:
                raise RuntimeError("Bad message")

            await self.q.put(
                (data["id"], data["service"], data["request"])
            )

        except Exception as e:
            print("receive exception:", str(e), flush=True)
            await self.ws.send_json({"error": str(e)})

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
            
        # Wait for outstanding requests to go below MAX_OUTSTANDING_REQUESTS
        while len(workers) > MAX_OUTSTANDING_REQUESTS:

            # Fixes deadlock
            # FIXME: Put it in its own loop
            await asyncio.sleep(START_REQUEST_WAIT)

            await self.maybe_tidy_workers(workers)

        async def responder(resp, fin):
            await self.ws.send_json({
                "id": id,
                "response": resp,
                "complete": fin,
            })

        worker = asyncio.create_task(
            self.request_task(request, responder, "0000", svc)
        )

        workers.append(worker)

    async def request_task(self, request, responder, flow, svc):

        try:
            dispatcher = self.dispatcher_manager.dispatch_service()
            await dispatcher.invoke(request, responder, "0000", svc)
        except Exception as e:
            await self.ws.send_json({"error": str(e)})

    async def run(self):

        # Worker threads, servicing
        workers = []

        while self.running.get():

            try:

                if len(workers) > 0:
                    await self.maybe_tidy_workers(workers)

                # Get next request on queue
                id, svc, request = await asyncio.wait_for(self.q.get(), 1)

            except TimeoutError:
                continue

            except Exception as e:
                # This is an internal working error, may not be recoverable
                print("run prepare exception:", e)
                await self.ws.send_json({"id": id, "error": str(e)})
                self.running.stop()

                if self.ws:
                    self.ws.close()
                    self.ws = None

                break

            try:
                print(id, svc, request)

                await self.start_request_task(
                    self.ws, id, svc, request, workers
                )

            except Exception as e:
                print("Exception2:", e)
                await self.ws.send_json({"error": str(e)})

        self.running.stop()

        if self.ws:
            self.ws.close()
            self.ws = None

