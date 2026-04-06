
from aiohttp import web
import yaml
import zipfile
from io import BytesIO
import importlib.resources
import json

from . generator import Generator
from . import Index, Packager

import logging
logger = logging.getLogger("api")
logger.setLevel(logging.INFO)

class Api:
    def __init__(self, **config):

        self.port = int(config.get("port", "8080"))
        self.app = web.Application(middlewares=[])

        self.app.add_routes([
            web.post("/api/generate/{platform}/{template}", self.generate)
        ])

        self.ui = importlib.resources.files().joinpath("ui")

        self.app.add_routes([
            web.get("/api/latest-stable", self.latest_stable),
            web.get("/api/latest", self.latest),
            web.get("/api/versions", self.versions),
        ])

        self.app.add_routes([
            web.get("/api/dialog-flow", self.get_dialog_flow),
            web.get("/api/config-prepare", self.get_config_prepare),
            web.get("/api/docs-manifest", self.get_docs_manifest),
            web.get("/api/docs/{path:.*}", self.get_docs_fragment),
        ])

    def latest(self, request):

        latest = Index.get_latest()

        return web.json_response(
            {
                "template": latest.name,
                "version": latest.version,
            }
        )

    def latest_stable(self, request):

        latest = Index.get_latest_stable()

        return web.json_response(
            {
                "template": latest.name,
                "version": latest.version,
            }
        )

    def versions(self, request):

        versions = Index.get_templates()

        return web.json_response([
            {
                "template": v.name,
                "version": v.version,
                "description": v.description,
                "status": v.status,
            }
            for v in versions
        ])

    def load_dialog_resource(self, filename):
        """Load a dialog flow resource file from resources/dialog/"""
        resources = importlib.resources.files().joinpath("resources").joinpath("dialog")
        path = resources.joinpath(filename)
        try:
            return path.read_text()
        except:
            raise web.HTTPNotFound()

    def get_dialog_flow(self, request):
        """Return dialog flow YAML"""
        content = self.load_dialog_resource("trustgraph-flow.yaml")
        return web.Response(text=content, content_type="application/x-yaml")

    def get_config_prepare(self, request):
        """Return config preparation JSONata transform"""
        content = self.load_dialog_resource("trustgraph-output.jsonata")
        return web.Response(text=content, content_type="text/plain")

    def get_docs_manifest(self, request):
        """Return documentation manifest YAML"""
        content = self.load_dialog_resource("trustgraph-docs.yaml")
        return web.Response(text=content, content_type="application/x-yaml")

    def get_docs_fragment(self, request):
        """Return a documentation markdown fragment"""
        path = request.match_info["path"]
        # Validate path to prevent directory traversal
        if ".." in path:
            raise web.HTTPNotFound()
        content = self.load_dialog_resource(f"docs/{path}")
        return web.Response(text=content, content_type="text/markdown")

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

    async def generate(self, request):

        logger.info("Generate...")

        try:
            platform = request.match_info["platform"]
        except:
            platform = "docker-compose"

        try:
            template = request.match_info["template"]
        except:
            return web.HTTPBadRequest()

        logger.info(f"Generating for platform={platform} template={template}")

        try:

            config = await request.text()

            # **************************************************************
            # This is a security boundary!  This is used by jsonnet, so if
            # a user can provide jsonnet, they can execute anything server
            # side.
            # **************************************************************

            # This verifies/forces that the input is JSON.  Important because
            # input is user-supplied, don't want to trust it.
            try:
                dec = json.loads(config)
                config = json.dumps(dec)
            except:
                # Incorrectly formatted stuff is not our problem,
                logger.info(f"Bad JSON")
                return web.HTTPBadRequest()

            logger.info(f"Config: {config}")

            pkg = Packager(
                version = None,      # Use version from template configuration
                template = template,
                platform = platform,
                latest = False,
                latest_stable = False
            )

            data = pkg.generate(config)

            return web.Response(
                body = data,
                content_type = "application/octet-stream"
            )

        except Exception as e:
            logging.error(f"Exception: {e}")
            return web.HTTPInternalServerError()

    def run(self):

        web.run_app(self.app, port=self.port)

