
#
# This provides a Prometheus endpoint on the api-gateway.  It proxies
# HTTP GET requests to Prometheus.
# 

import aiohttp
from aiohttp import web
import asyncio
import uuid
import logging

from .. capabilities import enforce

logger = logging.getLogger("endpoint")
logger.setLevel(logging.INFO)

class MetricsEndpoint:

    def __init__(self, prometheus_url, endpoint_path, auth, capability):

        self.prometheus_url = prometheus_url
        self.path = endpoint_path
        self.auth = auth
        self.capability = capability

    async def start(self):
        pass

    def add_routes(self, app):

        app.add_routes([
            web.get(self.path + "/{path:.*}", self.handle),
        ])

    async def handle(self, request):

        logger.debug(f"Processing metrics request: {request.path}")

        await enforce(request, self.auth, self.capability)

        path = request.match_info["path"]
        url = (
            self.prometheus_url + "/api/v1/" + path + "?" +
            request.query_string
        )

        try:

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    return web.Response(
                        status=resp.status,
                        text=await resp.text()
                    )

        except aiohttp.ClientConnectionError as e:

            # Upstream unreachable (connect refused, DNS failure,
            # server disconnect).  Distinguish from our own errors so
            # callers know where the fault is.
            logger.error(f"Metrics upstream {url} unreachable: {e}")
            return web.Response(
                status=502,
                text=f"Bad Gateway: metrics upstream unreachable: {e}",
            )

        except Exception as e:

            logger.error(f"Metrics proxy exception: {e}", exc_info=True)
            return web.Response(
                status=500,
                text=f"Internal Server Error: {e}",
            )

