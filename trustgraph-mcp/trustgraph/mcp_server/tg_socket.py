
from websockets.asyncio.client import connect
import asyncio
import logging
import json
import uuid
import hashlib

logger = logging.getLogger(__name__)


def _token_key(token):
    """Derive a dict key from a token without storing the raw secret."""
    return hashlib.sha256(token.encode()).hexdigest()[:16]


class WebSocketManager:
    """Manages an authenticated WebSocket connection to the TrustGraph
    gateway on behalf of a single caller.

    Each caller token gets its own WebSocketManager so that gateway-side
    identity, workspace, and capability scoping are preserved end-to-end.
    """

    def __init__(self, url, token):
        self.url = url
        # ── Security boundary: token storage ──
        # This is the MCP caller's Bearer token, forwarded verbatim to
        # the gateway.  It MUST NOT be logged, persisted, or shared
        # across callers.  It is held only for the lifetime of this
        # connection so that re-auth (e.g. after a reconnect) is
        # possible.
        self.token = token
        self.socket = None
        self.identity = None
        self.last_used = None

    async def start(self):
        """Connect and authenticate via the gateway's in-band auth
        protocol.  Raises on auth failure."""

        # ── Security boundary: MCP server → gateway ──
        # The WebSocket connects to the gateway and authenticates using
        # the caller's Bearer token via the in-band first-frame auth
        # protocol.  The token belongs to the MCP client — we forward
        # it as-is and never interpret its contents.
        self.socket = await connect(self.url)
        self.pending_requests = {}
        self.running = True

        await self._authenticate()

        self.reader_task = asyncio.create_task(self.reader())

    async def _authenticate(self):
        """Send in-band auth frame and wait for auth-ok / auth-failed.

        The gateway expects ``{"type": "auth", "token": "..."}`` as the
        first frame on a new WebSocket.  Any service frame sent before
        auth-ok is rejected.
        """
        await self.socket.send(json.dumps({
            "type": "auth",
            "token": self.token,
        }))

        response_text = await asyncio.wait_for(self.socket.recv(), 10)
        response = json.loads(response_text)

        if response.get("type") == "auth-ok":
            logger.info(
                "WebSocket authenticated, default workspace: %s",
                response.get("workspace"),
            )
            return

        # Auth failed — close immediately, do not leave an
        # unauthenticated socket open.
        await self.socket.close()
        self.socket = None

        if response.get("type") == "auth-failed":
            raise RuntimeError(
                "Gateway rejected the authentication token"
            )

        raise RuntimeError(
            f"Unexpected auth response type: {response.get('type')}"
        )

    async def whoami(self):
        """Verify the token by calling the gateway's whoami endpoint.
        Returns the identity dict and caches it on ``self.identity``.
        """
        gen = self.request("iam", {"operation": "whoami"}, flow_id=None)
        async for response in gen:
            self.identity = response
            return response

    async def stop(self):
        self.running = False
        if hasattr(self, "reader_task"):
            await self.reader_task

    async def reader(self):
        """Background task: read WebSocket frames and route them to the
        correct pending-request queue by ``id``."""

        while self.running:
            try:

                try:
                    response_text = await asyncio.wait_for(
                        self.socket.recv(), 0.5
                    )
                except TimeoutError:
                    continue

                response = json.loads(response_text)

                request_id = response.get("id")
                if request_id and request_id in self.pending_requests:
                    queue = self.pending_requests[request_id]
                    await queue.put(response)
                else:
                    logger.warning(
                        "Response for unknown request ID: %s", request_id
                    )

            except Exception as e:

                logger.error("Error in websocket reader: %s", e)

                for queue in self.pending_requests.values():
                    try:
                        await queue.put({"error": str(e)})
                    except Exception:
                        pass

                self.pending_requests.clear()
                break

        await self.socket.close()
        self.socket = None

    async def request(
            self, service, request_data, flow_id="default",
            workspace=None,
    ):
        """Send a request via WebSocket and yield responses.

        Args:
            service: Gateway service name (e.g. "graph-rag", "config").
            request_data: Inner request payload.
            flow_id: Optional flow identifier.  ``None`` omits the field
                (workspace-level services don't use flows).
            workspace: Optional workspace override.  When ``None`` the
                gateway uses the caller's default workspace.
        """

        import time
        self.last_used = time.monotonic()

        request_id = f"{uuid.uuid4()}"

        response_queue = asyncio.Queue()
        self.pending_requests[request_id] = response_queue

        try:

            message = {
                "id": request_id,
                "service": service,
                "request": request_data,
            }

            if flow_id is not None:
                message["flow"] = flow_id

            # ── Security boundary: workspace scoping ──
            # When the caller supplies a workspace, we set it on the
            # message envelope.  The gateway's enforce_workspace()
            # validates that the authenticated identity is permitted
            # to access the target workspace — we MUST NOT skip or
            # override that check.  When workspace is None, the
            # gateway default-fills from the identity's bound workspace.
            if workspace is not None:
                message["workspace"] = workspace

            await self.socket.send(json.dumps(message))

            while self.running:

                try:
                    response = await asyncio.wait_for(
                        response_queue.get(), 0.5
                    )
                except TimeoutError:
                    continue

                if "error" in response:
                    if isinstance(response["error"], dict):
                        raise RuntimeError(
                            response["error"].get("message", str(response["error"]))
                        )
                    else:
                        raise RuntimeError(str(response["error"]))

                yield response["response"]

                if response.get("complete"):
                    break

        finally:
            self.pending_requests.pop(request_id, None)
