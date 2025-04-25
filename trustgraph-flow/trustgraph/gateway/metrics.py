
#
# This provides a Prometheus endpoint on the api-gateway.  It proxies
# HTTP GET requests to Prometheus.
# 

import aiohttp
from aiohttp import web
import asyncio
from pulsar.schema import JsonSchema
import uuid
import logging

logger = logging.getLogger("endpoint")
logger.setLevel(logging.INFO)

class MetricsEndpoint:

    def __init__(self, prometheus_url, endpoint_path, auth):

        self.prometheus_url = prometheus_url
        self.path = endpoint_path
        self.auth = auth
        self.operation = "service"

    async def start(self):
        pass

    def add_routes(self, app):

        app.add_routes([
            web.get(self.path + "/{path:.*}", self.handle),
        ])

    async def handle(self, request):

        print(request.path, "...")

        try:
            ht = request.headers["Authorization"]
            tokens = ht.split(" ", 2)
            if tokens[0] != "Bearer":
                return web.HTTPUnauthorized()
            token = tokens[1]
        except:
            token = ""

        if not self.auth.permitted(token, self.operation):
            return web.HTTPUnauthorized()

        try:

            path = request.match_info["path"]

            async with aiohttp.ClientSession() as session:

                url = (
                    self.prometheus_url + "/api/v1/" + path + "?" +
                    request.query_string
                )

                async with session.get(url) as resp:
                    return web.Response(
                        status=resp.status,
                        text=await resp.text()
                    )

        except Exception as e:

            logging.error(f"Exception: {e}")

            raise web.HTTPInternalServerError()

