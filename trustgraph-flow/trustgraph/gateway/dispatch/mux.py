
import asyncio
import queue
import uuid
import logging

# Module logger
logger = logging.getLogger(__name__)

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

            if "request" not in data:
                raise RuntimeError("Bad message")

            if "id" not in data:
                raise RuntimeError("Bad message")

            await self.q.put((
                    data["id"], data.get("flow"),
                    data["service"],
                    data["request"]
            ))

        except Exception as e:
            logger.error(f"Receive exception: {str(e)}", exc_info=True)
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

    async def start_request_task(self, ws, id, flow, svc, request, workers):
            
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
            self.request_task(request, responder, flow, svc)
        )

        workers.append(worker)

    async def request_task(self, request, responder, flow, svc):

        try:

            if flow:

                await self.dispatcher_manager.invoke_flow_service(
                    request, responder, flow, svc
                )

            else:

                await self.dispatcher_manager.invoke_global_service(
                    request, responder, svc
                )

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
                item = await asyncio.wait_for(self.q.get(), 1)
                id, flow, svc, request = item

            except TimeoutError:
                continue

            except Exception as e:
                # This is an internal working error, may not be recoverable
                logger.error(f"Run prepare exception: {e}", exc_info=True)
                await self.ws.send_json({"id": id, "error": str(e)})
                self.running.stop()

                if self.ws:
                    await self.ws.close()
                    self.ws = None

                break

            try:

                await self.start_request_task(
                    self.ws, id, flow, svc, request, workers
                )

            except Exception as e:
                logger.error(f"Exception in mux: {e}", exc_info=True)
                await self.ws.send_json({"error": str(e)})

        self.running.stop()

        if self.ws:
            await self.ws.close()
            self.ws = None

