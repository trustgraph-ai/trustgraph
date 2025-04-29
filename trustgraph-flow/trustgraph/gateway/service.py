"""
API gateway.  Offers HTTP services which are translated to interaction on the
Pulsar bus.
"""

module = "api-gateway"

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
import uuid
import json

import pulsar
from prometheus_client import start_http_server

from .. log_level import LogLevel

from . serialize import to_subgraph
from . running import Running

from .. schema import ConfigPush, config_push_queue

from . text_completion import TextCompletionRequestor
#from . prompt import PromptRequestor
#from . graph_rag import GraphRagRequestor
#from . document_rag import DocumentRagRequestor
#from . triples_query import TriplesQueryRequestor
#from . graph_embeddings_query import GraphEmbeddingsQueryRequestor
#from . embeddings import EmbeddingsRequestor
#from . encyclopedia import EncyclopediaRequestor
#from . agent import AgentRequestor
#from . dbpedia import DbpediaRequestor
#from . internet_search import InternetSearchRequestor
#from . librarian import LibrarianRequestor
from . config import ConfigRequestor
from . flow import FlowRequestor
#from . triples_stream import TriplesStreamEndpoint
#from . graph_embeddings_stream import GraphEmbeddingsStreamEndpoint
#from . document_embeddings_stream import DocumentEmbeddingsStreamEndpoint
#from . triples_load import TriplesLoadEndpoint
#from . graph_embeddings_load import GraphEmbeddingsLoadEndpoint
#from . document_embeddings_load import DocumentEmbeddingsLoadEndpoint
from . mux import MuxEndpoint
#from . document_load import DocumentLoadSender
#from . text_load import TextLoadSender
from . metrics import MetricsEndpoint

from . endpoint import ServiceEndpoint
from . flow_endpoint import FlowEndpoint
from . auth import Authenticator
from .. base import Subscriber
from .. base import Consumer

logger = logging.getLogger("api")
logger.setLevel(logging.INFO)

default_pulsar_host = os.getenv("PULSAR_HOST", "pulsar://pulsar:6650")
default_prometheus_url = os.getenv("PROMETHEUS_URL", "http://prometheus:9090")
default_pulsar_api_key = os.getenv("PULSAR_API_KEY", None)
default_timeout = 600
default_port = 8088
default_api_token = os.getenv("GATEWAY_SECRET", "")

class Api:

    def __init__(self, **config):

        self.port = int(config.get("port", default_port))
        self.timeout = int(config.get("timeout", default_timeout))
        self.pulsar_host = config.get("pulsar_host", default_pulsar_host)
        self.pulsar_api_key = config.get(
            "pulsar_api_key", default_pulsar_api_key
        )
        self.pulsar_listener = config.get("pulsar_listener", None)

        if self.pulsar_api_key:
            self.pulsar_client = pulsar.Client(
                self.pulsar_host, listener_name=self.pulsar_listener,
                authentication=pulsar.AuthenticationToken(self.pulsar_api_key)
            )
        else:
            self.pulsar_client = pulsar.Client(
                self.pulsar_host, listener_name=self.pulsar_listener,
            )

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
            # "text-completion": TextCompletionRequestor(
            #     pulsar_client=self.pulsar_client, timeout=self.timeout,
            #     auth = self.auth,
            # ),
            # "prompt": PromptRequestor(
            #     pulsar_client=self.pulsar_client, timeout=self.timeout,
            #     auth = self.auth,
            # ),
            # "graph-rag": GraphRagRequestor(
            #     pulsar_client=self.pulsar_client, timeout=self.timeout,
            #     auth = self.auth,
            # ),
            # "document-rag": DocumentRagRequestor(
            #     pulsar_client=self.pulsar_client, timeout=self.timeout,
            #     auth = self.auth,
            # ),
            # "triples-query": TriplesQueryRequestor(
            #     pulsar_client=self.pulsar_client, timeout=self.timeout,
            #     auth = self.auth,
            # ),
            # "graph-embeddings-query": GraphEmbeddingsQueryRequestor(
            #     pulsar_client=self.pulsar_client, timeout=self.timeout,
            #     auth = self.auth,
            # ),
            # "embeddings": EmbeddingsRequestor(
            #     pulsar_client=self.pulsar_client, timeout=self.timeout,
            #     auth = self.auth,
            # ),
            # "agent": AgentRequestor(
            #     pulsar_client=self.pulsar_client, timeout=self.timeout,
            #     auth = self.auth,
            # ),
            # "librarian": LibrarianRequestor(
            #     pulsar_client=self.pulsar_client, timeout=self.timeout,
            #     auth = self.auth,
            # ),
            "config": ConfigRequestor(
                pulsar_client=self.pulsar_client, timeout=self.timeout,
                auth = self.auth,
            ),
            "flow": FlowRequestor(
                pulsar_client=self.pulsar_client, timeout=self.timeout,
                auth = self.auth,
            ),
            # "encyclopedia": EncyclopediaRequestor(
            #     pulsar_client=self.pulsar_client, timeout=self.timeout,
            #     auth = self.auth,
            # ),
            # "dbpedia": DbpediaRequestor(
            #     pulsar_client=self.pulsar_client, timeout=self.timeout,
            #     auth = self.auth,
            # ),
            # "internet-search": InternetSearchRequestor(
            #     pulsar_client=self.pulsar_client, timeout=self.timeout,
            #     auth = self.auth,
            # ),
            # "document-load": DocumentLoadSender(
            #     pulsar_client=self.pulsar_client,
            # ),
            # "text-load": TextLoadSender(
            #     pulsar_client=self.pulsar_client,
            # ),
        }

        self.endpoints = [
            # ServiceEndpoint(
            #     endpoint_path = "/api/v1/text-completion", auth=self.auth,
            #     requestor = self.services["text-completion"],
            # ),
            # ServiceEndpoint(
            #     endpoint_path = "/api/v1/prompt", auth=self.auth,
            #     requestor = self.services["prompt"],
            # ),
            # ServiceEndpoint(
            #     endpoint_path = "/api/v1/graph-rag", auth=self.auth,
            #     requestor = self.services["graph-rag"],
            # ),
            # ServiceEndpoint(
            #     endpoint_path = "/api/v1/document-rag", auth=self.auth,
            #     requestor = self.services["document-rag"],
            # ),
            # ServiceEndpoint(
            #     endpoint_path = "/api/v1/triples-query", auth=self.auth,
            #     requestor = self.services["triples-query"],
            # ),
            # ServiceEndpoint(
            #     endpoint_path = "/api/v1/graph-embeddings-query",
            #     auth=self.auth,
            #     requestor = self.services["graph-embeddings-query"],
            # ),
            # ServiceEndpoint(
            #     endpoint_path = "/api/v1/embeddings", auth=self.auth,
            #     requestor = self.services["embeddings"],
            # ),
            # ServiceEndpoint(
            #     endpoint_path = "/api/v1/agent", auth=self.auth,
            #     requestor = self.services["agent"],
            # ),
            # ServiceEndpoint(
            #     endpoint_path = "/api/v1/librarian", auth=self.auth,
            #     requestor = self.services["librarian"],
            # ),
            ServiceEndpoint(
                endpoint_path = "/api/v1/config", auth=self.auth,
                requestor = self.services["config"],
            ),
            ServiceEndpoint(
                endpoint_path = "/api/v1/flow", auth=self.auth,
                requestor = self.services["flow"],
            ),
            FlowEndpoint(
                endpoint_path = "/api/v1/flow/{flow}/{kind}",
                auth=self.auth,
                requestors = self.services,
            ),
            # ServiceEndpoint(
            #     endpoint_path = "/api/v1/encyclopedia", auth=self.auth,
            #     requestor = self.services["encyclopedia"],
            # ),
            # ServiceEndpoint(
            #     endpoint_path = "/api/v1/dbpedia", auth=self.auth,
            #     requestor = self.services["dbpedia"],
            # ),
            # ServiceEndpoint(
            #     endpoint_path = "/api/v1/internet-search", auth=self.auth,
            #     requestor = self.services["internet-search"],
            # ),
            # ServiceEndpoint(
            #     endpoint_path = "/api/v1/load/document", auth=self.auth,
            #     requestor = self.services["document-load"],
            # ),
            # ServiceEndpoint(
            #     endpoint_path = "/api/v1/load/text", auth=self.auth,
            #     requestor = self.services["text-load"],
            # ),
            # TriplesStreamEndpoint(
            #     pulsar_client=self.pulsar_client,
            #     auth = self.auth,
            # ),
            # GraphEmbeddingsStreamEndpoint(
            #     pulsar_client=self.pulsar_client,
            #     auth = self.auth,
            # ),
            # DocumentEmbeddingsStreamEndpoint(
            #     pulsar_client=self.pulsar_client,
            #     auth = self.auth,
            # ),
            # TriplesLoadEndpoint(
            #     pulsar_client=self.pulsar_client,
            #     auth = self.auth,
            # ),
            # GraphEmbeddingsLoadEndpoint(
            #     pulsar_client=self.pulsar_client,
            #     auth = self.auth,
            # ),
            # DocumentEmbeddingsLoadEndpoint(
            #     pulsar_client=self.pulsar_client,
            #     auth = self.auth,
            # ),
            # MuxEndpoint(
            #     pulsar_client=self.pulsar_client,
            #     auth = self.auth,
            #     services = self.services,
            # ),
            MetricsEndpoint(
                endpoint_path = "/api/v1/metrics",
                prometheus_url = self.prometheus_url,
                auth = self.auth,
            ),
        ]

        self.flows = {}

#        self.services = {}

    async def on_config(self, msg, proc, flow):

        try:

            v = msg.value()

            print(f"Config version", v.version)

            if "flows" in v.config:

                flows = v.config["flows"]

                wanted = list(flows.keys())
                current = list(self.flows.keys())

                for k in wanted:
                    if k not in current:
                        self.flows[k] = json.loads(flows[k])
                        await self.start_flow(k, self.flows[k])

                for k in current:
                    if k not in wanted:
                        await self.stop_flow(k, self.flows[k])
                        del self.flows[k]

        except Exception as e:
            print(f"Exception: {e}", flush=True)

    async def start_flow(self, id, flow):
        print("Start flow", id)
        intf = flow["interfaces"]

        if "text-completion" in intf:
            k = (id, "text-completion")
            if k in self.services:
                await self.services[k].stop()
                del self.services[k]

            self.services[k] = TextCompletionRequestor(
                pulsar_client=self.pulsar_client, timeout=self.timeout,
                request_queue = intf["text-completion"]["request"],
                response_queue = intf["text-completion"]["response"],
                consumer = f"api-gateway-{id}-text-completion-request",
                subscriber = f"api-gateway-{id}-text-completion-request",
                auth = self.auth,
            )
            await self.services[k].start()

    async def stop_flow(self, id, flow):
        print("Stop flow", id)
        intf = flow["interfaces"]

        if "text-completion" in intf:
            k = (id, "text-completion")
            if k in self.services:
                await self.services[k].stop()
                del self.services[k]

    async def config_loader(self):

        async with asyncio.TaskGroup() as tg:

            id = str(uuid.uuid4())

            self.config_cons = Consumer(
                taskgroup = tg,
                flow = None,
                client = self.pulsar_client,
                subscriber = f"gateway-{id}",                
                topic = config_push_queue,
                schema = ConfigPush,
                handler = self.on_config,
                start_of_messages = True,
            )

            await self.config_cons.start()

            print("Waiting...")

        print("Config consumer done. :/")

    async def app_factory(self):
        
        self.app = web.Application(
            middlewares=[],
            client_max_size=256 * 1024 * 1024
        )

        asyncio.create_task(self.config_loader())

        for ep in self.endpoints:
            ep.add_routes(self.app)

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
        '--pulsar-api-key',
        default=default_pulsar_api_key,
        help=f'Pulsar API key',
    )

    parser.add_argument(
        '--pulsar-listener',
        help=f'Pulsar listener (default: none)',
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

