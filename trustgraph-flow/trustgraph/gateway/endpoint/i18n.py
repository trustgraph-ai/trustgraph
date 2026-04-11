import logging

from aiohttp import web

from trustgraph.i18n import get_language_pack

logger = logging.getLogger("endpoint")
logger.setLevel(logging.INFO)


class I18nPackEndpoint:

    def __init__(self, endpoint_path: str, auth):
        self.path = endpoint_path
        self.auth = auth
        self.operation = "service"

    async def start(self):
        pass

    def add_routes(self, app):
        app.add_routes([
            web.get(self.path, self.handle),
        ])

    async def handle(self, request):
        logger.debug(f"Processing i18n pack request: {request.path}")

        token = ""
        try:
            ht = request.headers["Authorization"]
            tokens = ht.split(" ", 2)
            if tokens[0] != "Bearer":
                return web.HTTPUnauthorized()
            token = tokens[1]
        except Exception:
            token = ""

        if not self.auth.permitted(token, self.operation):
            return web.HTTPUnauthorized()

        lang = request.match_info.get("lang") or "en"
        pack = get_language_pack(lang)

        return web.json_response(pack)
