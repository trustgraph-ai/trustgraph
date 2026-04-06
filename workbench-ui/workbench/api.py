
import asyncio
import aiohttp
from aiohttp import web
import importlib.resources
import websockets.asyncio.client as wsclient

import logging
logger = logging.getLogger("api")
logger.setLevel(logging.INFO)

class Running:
    def __init__(self): self.running = True
    def get(self): return self.running
    def stop(self): self.running = False

class Api:
    def __init__(self, **config):

        self.port = int(config.get("port", "8888"))
        self.gateway = config.get("gateway", "http://api-gateway:8088")

        if self.gateway[-1] != "/":
            self.gateway += "/"

        self.gateway_ws = self.gateway.replace(
            "https://", "wss://"
        ).replace(
            "http://", "ws://"
        )

        self.app = web.Application(middlewares=[])

        # Just pass-through some calls to the API back-end
        self.app.add_routes([web.get("/api/socket", self.socket)])
        self.app.add_routes([web.get("/api/export-core", self.export_core)])
        self.app.add_routes([web.post("/api/import-core", self.import_core)])

        # Everything else gets matched for serving static resources
        self.app.add_routes([web.get("/{tail:.*}", self.everything)])

        self.ui = importlib.resources.files().joinpath("ui")

    def open(self, path):

        if ".." in path:
            raise web.HTTPNotFound()

        if len(path) > 0:
            if path[0] == "/":
                path = path[1:]

        if path == "": path = "index.html"

        try:
            p = self.ui.joinpath(path)
            t = p.read_text()
            return t
        except:
            raise web.HTTPNotFound()

    def open_binary(self, path):

        if ".." in path:
            raise web.HTTPNotFound()

        if len(path) > 0:
            if path[0] == "/":
                path = path[1:]

        if path == "": path = "index.html"

        try:
            p = self.ui.joinpath(path)
            t = p.read_bytes()
            return t
        except:
            raise web.HTTPNotFound()

    async def everything(self, request):

        try:

            if request.path.endswith(".css"):
                t = self.open(request.path)
                return web.Response(
                    text=t, content_type="text/css"
                )

            if request.path.endswith(".png"):
                t = self.open_binary(request.path)
                return web.Response(
                    body=t, content_type="image/png"
                )

            if request.path.endswith(".svg"):
                t = self.open(request.path)
                return web.Response(
                    text=t, content_type="image/svg+xml"
                )

            if request.path.endswith(".js"):
                t = self.open(request.path)
                return web.Response(
                    text=t, content_type="text/javascript"
                )

            if request.path == "/" or request.path.endswith(".html"):
                t = self.open(request.path)
                return web.Response(
                    text=t, content_type="text/html"
                )

            # Fallback to index.html for client-side routing (SPA)
            # This allows React Router routes like /flows, /ontologies to work
            t = self.open("index.html")
            return web.Response(
                text=t, content_type="text/html"
            )

        except Exception as e:
            logging.error(f"Exception: {e}")
            raise web.HTTPInternalServerError()

    async def import_core(self, request):

        url = self.gateway + "api/v1/import-core?" + request.query_string

        async def sender():
            content = request.content
            data = await content.read(64*1024)

            while len(data) > 0:
                yield data
                data = await content.read(64*1024)

        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=sender()) as resp:
                return web.Response(status=200)

    async def export_core(self, request):

        url = self.gateway + "api/v1/export-core?" + request.query_string

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:

                response = web.StreamResponse(
                    status = 200, reason = "OK",
                    headers = {"Content-Type": "application/octet-stream"}
                )
                await response.prepare(request)

                content = resp.content

                while True:

                    data = await content.read(64*1024)

                    if len(data) == 0: break

                    if data is None: break

                    await response.write(data)

                return response

    async def socket(self, request):

        # Max message size is 50MB
        ws_server = web.WebSocketResponse(max_msg_size=52428800)

        await ws_server.prepare(request)

        url = self.gateway_ws + "api/v1/socket"

        running = Running()

        async with wsclient.connect(url, max_size=52428800) as ws_client:

            async def outbound(ws_from, ws_to, running):

                while running.get():

                    try:
                        msg = await ws_from.receive(timeout=2)
                    except TimeoutError:
                        continue

                    mt = msg.type
                    md = msg.data

                    if mt == aiohttp.WSMsgType.TEXT:
                        await ws_to.send(md)
                    elif mt == aiohttp.WSMsgType.BINARY:
                        await ws_to.send_bytes(md)
                    elif mt == aiohttp.WSMsgType.PING:
                        await ws_to.ping()
                    elif mt == aiohttp.WSMsgType.PONG:
                        await ws_to.pong()
                    elif mt == aiohttp.WSMsgType.CLOSE:
                        break
                    else:
                        print("Weird message", mt)
                        break

                running.stop()

            async def inbound(ws_from, ws_to, running):

                while running.get():

                    try:
                        msg = await asyncio.wait_for(
                            ws_from.recv(),
                            2
                        )
                    except TimeoutError:
                        continue
                    except Exception as e:
                        print(e)
                        break

                    await ws_to.send_str(msg)

                running.stop()

            s2c_task = asyncio.create_task(
                inbound(ws_client, ws_server, running)
            )

            await outbound(ws_server, ws_client, running)

            running.stop()

            await ws_server.close()
            await ws_client.close()

            await s2c_task

        return ws_server

    def run(self):

        web.run_app(self.app, port=self.port)

