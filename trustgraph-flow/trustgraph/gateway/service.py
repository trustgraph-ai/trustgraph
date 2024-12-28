"""
API gateway.  Offers HTTP services which are translated to interaction on the
Pulsar bus.
"""

module = ".".join(__name__.split(".")[1:-1])

# FIXME: Subscribes to Pulsar unnecessarily, should only do it when there
# are active listeners

# FIXME: Connection errors in publishers / subscribers cause those threads
# to fail and are not failed or retried

import asyncio
import argparse
from aiohttp import web
import logging
import os
import base64

import pulsar
from pulsar.schema import JsonSchema
from prometheus_client import start_http_server

from .. log_level import LogLevel

from .. schema import Metadata, Document, TextDocument
from .. schema import document_ingest_queue, text_ingest_queue

from . serialize import to_subgraph
from . running import Running
from . publisher import Publisher
from . subscriber import Subscriber
from . text_completion import TextCompletionRequestor
from . prompt import PromptRequestor
from . graph_rag import GraphRagRequestor
from . triples_query import TriplesQueryRequestor
from . graph_embeddings_query import GraphEmbeddingsQueryRequestor
from . embeddings import EmbeddingsRequestor
from . encyclopedia import EncyclopediaRequestor
from . agent import AgentRequestor
from . dbpedia import DbpediaRequestor
from . internet_search import InternetSearchRequestor
from . triples_stream import TriplesStreamEndpoint
from . graph_embeddings_stream import GraphEmbeddingsStreamEndpoint
from . triples_load import TriplesLoadEndpoint
from . graph_embeddings_load import GraphEmbeddingsLoadEndpoint
from . mux import MuxEndpoint

from . endpoint import ServiceEndpoint
from . auth import Authenticator

logger = logging.getLogger("api")
logger.setLevel(logging.INFO)

default_pulsar_host = os.getenv("PULSAR_HOST", "pulsar://pulsar:6650")
default_timeout = 600
default_port = 8088
default_api_token = os.getenv("GATEWAY_SECRET", "")

class Api:

    def __init__(self, **config):

        self.app = web.Application(
            middlewares=[],
            client_max_size=256 * 1024 * 1024
        )

        self.port = int(config.get("port", default_port))
        self.timeout = int(config.get("timeout", default_timeout))
        self.pulsar_host = config.get("pulsar_host", default_pulsar_host)

        api_token = config.get("api_token", default_api_token)

        # Token not set, or token equal empty string means no auth
        if api_token:
            self.auth = Authenticator(token=api_token)
        else:
            self.auth = Authenticator(allow_all=True)

        self.services = {
            "text-completion": TextCompletionRequestor(
                pulsar_host=self.pulsar_host, timeout=self.timeout,
                auth = self.auth,
            ),
            "prompt": PromptRequestor(
                pulsar_host=self.pulsar_host, timeout=self.timeout,
                auth = self.auth,
            ),
            "graph-rag": GraphRagRequestor(
                pulsar_host=self.pulsar_host, timeout=self.timeout,
                auth = self.auth,
            ),
            "triples-query": TriplesQueryRequestor(
                pulsar_host=self.pulsar_host, timeout=self.timeout,
                auth = self.auth,
            ),
            "graph-embeddings-query": GraphEmbeddingsQueryRequestor(
                pulsar_host=self.pulsar_host, timeout=self.timeout,
                auth = self.auth,
            ),
            "embeddings": EmbeddingsRequestor(
                pulsar_host=self.pulsar_host, timeout=self.timeout,
                auth = self.auth,
            ),
            "agent": AgentRequestor(
                pulsar_host=self.pulsar_host, timeout=self.timeout,
                auth = self.auth,
            ),
            "encyclopedia": EncyclopediaRequestor(
                pulsar_host=self.pulsar_host, timeout=self.timeout,
                auth = self.auth,
            ),
            "dbpedia": DbpediaRequestor(
                pulsar_host=self.pulsar_host, timeout=self.timeout,
                auth = self.auth,
            ),
            "internet-search": InternetSearchRequestor(
                pulsar_host=self.pulsar_host, timeout=self.timeout,
                auth = self.auth,
            ),
        }

        self.endpoints = [
            ServiceEndpoint(
                endpoint_path = "/api/v1/text-completion", auth=self.auth,
                requestor = self.services["text-completion"],
            ),
            ServiceEndpoint(
                endpoint_path = "/api/v1/prompt", auth=self.auth,
                requestor = self.services["prompt"],
            ),
            ServiceEndpoint(
                endpoint_path = "/api/v1/graph-rag", auth=self.auth,
                requestor = self.services["graph-rag"],
            ),
            ServiceEndpoint(
                endpoint_path = "/api/v1/triples-query", auth=self.auth,
                requestor = self.services["triples-query"],
            ),
            ServiceEndpoint(
                endpoint_path = "/api/v1/graph-embeddings-query",
                auth=self.auth,
                requestor = self.services["graph-embeddings-query"],
            ),
            ServiceEndpoint(
                endpoint_path = "/api/v1/embeddings", auth=self.auth,
                requestor = self.services["embeddings"],
            ),
            ServiceEndpoint(
                endpoint_path = "/api/v1/agent", auth=self.auth,
                requestor = self.services["agent"],
            ),
            ServiceEndpoint(
                endpoint_path = "/api/v1/encyclopedia", auth=self.auth,
                requestor = self.services["encyclopedia"],
            ),
            ServiceEndpoint(
                endpoint_path = "/api/v1/dbpedia", auth=self.auth,
                requestor = self.services["dbpedia"],
            ),
            ServiceEndpoint(
                endpoint_path = "/api/v1/internet-search", auth=self.auth,
                requestor = self.services["internet-search"],
            ),
            TriplesStreamEndpoint(
                pulsar_host=self.pulsar_host,
                auth = self.auth,
            ),
            GraphEmbeddingsStreamEndpoint(
                pulsar_host=self.pulsar_host,
                auth = self.auth,
            ),
            TriplesLoadEndpoint(
                pulsar_host=self.pulsar_host,
                auth = self.auth,
            ),
            GraphEmbeddingsLoadEndpoint(
                pulsar_host=self.pulsar_host,
                auth = self.auth,
            ),
            MuxEndpoint(
                pulsar_host=self.pulsar_host,
                auth = self.auth,
                services = self.services,
            ),
        ]

        self.document_out = Publisher(
            self.pulsar_host, document_ingest_queue,
            schema=JsonSchema(Document),
            chunking_enabled=True,
        )

        self.text_out = Publisher(
            self.pulsar_host, text_ingest_queue,
            schema=JsonSchema(TextDocument),
            chunking_enabled=True,
        )

        for ep in self.endpoints:
            ep.add_routes(self.app)

        self.app.add_routes([
            web.post("/api/v1/load/document", self.load_document),
            web.post("/api/v1/load/text", self.load_text),
        ])

    async def load_document(self, request):

        try:

            data = await request.json()

            if "metadata" in data:
                metadata = to_subgraph(data["metadata"])
            else:
                metadata = []

            # Doing a base64 decoe/encode here to make sure the
            # content is valid base64
            doc = base64.b64decode(data["data"])

            resp = await asyncio.to_thread(
                self.document_out.send,
                None,
                Document(
                    metadata=Metadata(
                        id=data.get("id"),
                        metadata=metadata,
                        user=data.get("user", "trustgraph"),
                        collection=data.get("collection", "default"),
                    ),
                    data=base64.b64encode(doc).decode("utf-8")
                )
            )

            print("Document loaded.")

            return web.json_response(
                { }
            )

        except Exception as e:
            logging.error(f"Exception: {e}")

            return web.json_response(
                { "error": str(e) }
            )

    async def load_text(self, request):

        try:

            data = await request.json()

            if "metadata" in data:
                metadata = to_subgraph(data["metadata"])
            else:
                metadata = []

            if "charset" in data:
                charset = data["charset"]
            else:
                charset = "utf-8"

            # Text is base64 encoded
            text = base64.b64decode(data["text"]).decode(charset)

            resp = await asyncio.to_thread(
                self.text_out.send,
                None,
                TextDocument(
                    metadata=Metadata(
                        id=data.get("id"),
                        metadata=metadata,
                        user=data.get("user", "trustgraph"),
                        collection=data.get("collection", "default"),
                    ),
                    text=text,
                )
            )

            print("Text document loaded.")

            return web.json_response(
                { }
            )

        except Exception as e:
            logging.error(f"Exception: {e}")

            return web.json_response(
                { "error": str(e) }
            )

    async def app_factory(self):

        for ep in self.endpoints:
            await ep.start()

        self.document_out.start()
        self.text_out.start()

        return self.app

    def run(self):
        web.run_app(self.app_factory(), port=self.port)

def run():

    parser = argparse.ArgumentParser(
        prog="api-gateway",
        description=__doc__
    )

    parser.add_argument(
        '-p', '--pulsar-host',
        default=default_pulsar_host,
        help=f'Pulsar host (default: {default_pulsar_host})',
    )

    parser.add_argument(
        '--port',
        type=int,
        default=default_port,
        help=f'Port number to listen on (default: {default_port})',
    )

    parser.add_argument(
        '--timeout',
        type=int,
        default=default_timeout,
        help=f'API request timeout in seconds (default: {default_timeout})',
    )

    parser.add_argument(
        '--api-token',
        default=default_api_token,
        help=f'Secret API token (default: no auth)',
    )

    parser.add_argument(
        '-l', '--log-level',
        type=LogLevel,
        default=LogLevel.INFO,
        choices=list(LogLevel),
        help=f'Output queue (default: info)'
    )

    parser.add_argument(
        '--metrics',
        action=argparse.BooleanOptionalAction,
        default=True,
        help=f'Metrics enabled (default: true)',
    )

    parser.add_argument(
        '-P', '--metrics-port',
        type=int,
        default=8000,
        help=f'Prometheus metrics port (default: 8000)',
    )

    args = parser.parse_args()
    args = vars(args)

    if args["metrics"]:
        start_http_server(args["metrics_port"])

    a = Api(**args)
    a.run()

