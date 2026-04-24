
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

    def __init__(self, dispatcher_manager, ws, running, auth):
        """
        ``auth`` is required — the Mux implements the first-frame
        auth protocol described in ``iam.md`` and will refuse any
        non-auth frame until an ``auth-ok`` has been issued.  There
        is no no-auth mode.
        """
        if auth is None:
            raise ValueError(
                "Mux requires an 'auth' argument — there is no "
                "no-auth mode"
            )

        self.dispatcher_manager = dispatcher_manager
        self.ws = ws
        self.running = running
        self.auth = auth

        # Authenticated identity, populated by the first-frame auth
        # protocol.  ``None`` means the socket is not yet
        # authenticated; any non-auth frame is refused.
        self.identity = None

        self.q = asyncio.Queue(maxsize=MAX_QUEUE_SIZE)

    async def destroy(self):

        self.running.stop()

        if self.ws:
            await self.ws.close()

    async def _handle_auth_frame(self, data):
        """Process a ``{"type": "auth", "token": "..."}`` frame.
        On success, updates ``self.identity`` and returns an
        ``auth-ok`` response frame.  On failure, returns the masked
        auth-failure frame.  Never raises — auth failures keep the
        socket open so the client can retry without reconnecting
        (important for browsers, which treat a handshake-time 401
        as terminal)."""
        token = data.get("token", "")
        if not token:
            await self.ws.send_json({
                "type": "auth-failed",
                "error": "auth failure",
            })
            return

        class _Shim:
            def __init__(self, tok):
                self.headers = {"Authorization": f"Bearer {tok}"}

        try:
            identity = await self.auth.authenticate(_Shim(token))
        except Exception:
            await self.ws.send_json({
                "type": "auth-failed",
                "error": "auth failure",
            })
            return

        self.identity = identity
        await self.ws.send_json({
            "type": "auth-ok",
            "workspace": identity.workspace,
        })

    async def receive(self, msg):

        request_id = None

        try:

            data = msg.json()

            # In-band auth protocol: the client sends
            # ``{"type": "auth", "token": "..."}`` as its first frame
            # (and any time it wants to re-auth: JWT refresh, token
            # rotation, etc).  Auth is always required on a Mux —
            # there is no no-auth mode.
            if isinstance(data, dict) and data.get("type") == "auth":
                await self._handle_auth_frame(data)
                return

            request_id = data.get("id")

            if "request" not in data:
                raise RuntimeError("Bad message")

            if "id" not in data:
                raise RuntimeError("Bad message")

            # Reject all non-auth frames until an ``auth-ok`` has
            # been issued.
            if self.identity is None:
                await self.ws.send_json({
                    "id": request_id,
                    "error": {
                        "message": "auth failure",
                        "type": "auth-required",
                    },
                    "complete": True,
                })
                return

            # Workspace resolution.  Role workspace scope determines
            # which target workspaces are permitted.  The resolved
            # value is written to both the envelope and the inner
            # request payload so clients don't have to repeat it
            # per-message (same convenience HTTP callers get via
            # enforce_workspace).
            from ..capabilities import enforce_workspace
            from aiohttp import web as _web

            try:
                enforce_workspace(data, self.identity)
                inner = data.get("request")
                if isinstance(inner, dict):
                    enforce_workspace(inner, self.identity)
            except _web.HTTPForbidden:
                await self.ws.send_json({
                    "id": request_id,
                    "error": {
                        "message": "access denied",
                        "type": "access-denied",
                    },
                    "complete": True,
                })
                return

            workspace = data["workspace"]

            await self.q.put((
                    data["id"],
                    workspace,
                    data.get("flow"),
                    data["service"],
                    data["request"]
            ))

        except Exception as e:
            logger.error(f"Receive exception: {str(e)}", exc_info=True)
            error_resp = {
                "error": {"message": str(e), "type": "error"},
                "complete": True,
            }
            if request_id:
                error_resp["id"] = request_id
            await self.ws.send_json(error_resp)

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

    async def start_request_task(
        self, ws, id, workspace, flow, svc, request, workers,
    ):

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
            self.request_task(
                id, request, responder, workspace, flow, svc,
            )
        )

        workers.append(worker)

    async def request_task(
        self, id, request, responder, workspace, flow, svc,
    ):

        try:

            if flow:

                await self.dispatcher_manager.invoke_flow_service(
                    request, responder, workspace, flow, svc,
                )

            else:

                await self.dispatcher_manager.invoke_global_service(
                    request, responder, svc
                )

        except Exception as e:
            await self.ws.send_json({
                "id": id,
                "error": {"message": str(e), "type": "error"},
                "complete": True,
            })

    async def run(self):

        # Worker threads, servicing
        workers = []

        while self.running.get():

            try:

                if len(workers) > 0:
                    await self.maybe_tidy_workers(workers)

                # Get next request on queue
                item = await asyncio.wait_for(self.q.get(), 1)
                id, workspace, flow, svc, request = item

            except TimeoutError:
                continue

            except Exception as e:
                # This is an internal working error, may not be recoverable
                logger.error(f"Run prepare exception: {e}", exc_info=True)
                await self.ws.send_json({
                    "id": id,
                    "error": {"message": str(e), "type": "error"},
                    "complete": True,
                })
                self.running.stop()

                if self.ws:
                    await self.ws.close()
                    self.ws = None

                break

            try:

                await self.start_request_task(
                    self.ws, id, workspace, flow, svc, request, workers
                )

            except Exception as e:
                logger.error(f"Exception in mux: {e}", exc_info=True)
                await self.ws.send_json({
                    "id": id,
                    "error": {"message": str(e), "type": "error"},
                    "complete": True,
                })

        self.running.stop()

        if self.ws:
            await self.ws.close()
            self.ws = None

