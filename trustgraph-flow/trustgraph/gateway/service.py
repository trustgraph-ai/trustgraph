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

from . serialize import to_subgraph
from . running import Running
from . publisher import Publisher
from . subscriber import Subscriber
from . text_completion import TextCompletionRequestor
from . prompt import PromptRequestor
from . graph_rag import GraphRagRequestor
from . document_rag import DocumentRagRequestor
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
from . document_load import DocumentLoadSender
from . text_load import TextLoadSender
from . metrics import MetricsEndpoint

from . endpoint import ServiceEndpoint
from . auth import Authenticator

logger = logging.getLogger("api")
logger.setLevel(logging.INFO)

default_pulsar_host = os.getenv("PULSAR_HOST", "pulsar://pulsar:6650")
default_prometheus_url = os.getenv("PROMETHEUS_URL", "http://prometheus:9090")
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

        self.prometheus_url = config.get(
            "prometheus_url", default_prometheus_url,
        )

        if not self.prometheus_url.endswith("/"):
            self.prometheus_url += "/"

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
            "document-rag": DocumentRagRequestor(
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
            "document-load": DocumentLoadSender(
                pulsar_host=self.pulsar_host,
            ),
            "text-load": TextLoadSender(
                pulsar_host=self.pulsar_host,
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
                endpoint_path = "/api/v1/document-rag", auth=self.auth,
                requestor = self.services["document-rag"],
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
            ServiceEndpoint(
                endpoint_path = "/api/v1/load/document", auth=self.auth,
                requestor = self.services["document-load"],
            ),
            ServiceEndpoint(
                endpoint_path = "/api/v1/load/text", auth=self.auth,
                requestor = self.services["text-load"],
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
            MetricsEndpoint(
                endpoint_path = "/api/v1/metrics",
                prometheus_url = self.prometheus_url,
                auth = self.auth,
            ),
        ]

        for ep in self.endpoints:
            ep.add_routes(self.app)

    async def app_factory(self):

        for ep in self.endpoints:
            await ep.start()

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
        '-m', '--prometheus-url',
        default=default_prometheus_url,
        help=f'Prometheus URL (default: {default_prometheus_url})',
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

