import logging

from aiohttp import web

from trustgraph.i18n import get_language_pack

from .. capabilities import enforce

logger = logging.getLogger("endpoint")
logger.setLevel(logging.INFO)


class I18nPackEndpoint:

    def __init__(self, endpoint_path: str, auth, capability):
        self.path = endpoint_path
        self.auth = auth
        self.capability = capability

    async def start(self):
        pass

    def add_routes(self, app):
        app.add_routes([
            web.get(self.path, self.handle),
        ])

    async def handle(self, request):
        logger.debug(f"Processing i18n pack request: {request.path}")

        await enforce(request, self.auth, self.capability)

        lang = request.match_info.get("lang") or "en"

        # Path-traversal defense — critical, do not remove.
        if "/" in lang or ".." in lang:
            return web.HTTPBadRequest(reason="Invalid language code")

        pack = get_language_pack(lang)
        return web.json_response(pack)
