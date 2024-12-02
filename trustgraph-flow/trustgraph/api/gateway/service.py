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
from aiohttp import web, WSMsgType
import json
import logging
import uuid
import os
import base64

import pulsar
from pulsar.asyncio import Client
from pulsar.schema import JsonSchema
import _pulsar
from prometheus_client import start_http_server

from ... log_level import LogLevel

from ... schema import Value, Metadata, Document, TextDocument, Triple

from ... schema import Triples
from ... schema import triples_store_queue

from ... schema import GraphEmbeddings
from ... schema import graph_embeddings_store_queue

from ... schema import LookupRequest, LookupResponse

from ... schema import document_ingest_queue, text_ingest_queue

from . serialize import serialize_value, serialize_triple, serialize_subgraph
from . serialize import serialize_triples, serialize_graph_embeddings
from . serialize import to_value, to_subgraph

from . running import Running
from . publisher import Publisher
from . subscriber import Subscriber
from . endpoint import ServiceEndpoint, MultiResponseServiceEndpoint

from . text_completion import TextCompletionEndpoint
from . prompt import PromptEndpoint
from . graph_rag import GraphRagEndpoint
from . triples_query import TriplesQueryEndpoint
from . embeddings import EmbeddingsEndpoint
from . encyclopedia import EncyclopediaEndpoint
from . agent import AgentEndpoint
from . dbpedia import DbpediaEndpoint
from . internet_search import InternetSearchEndpoint
from . triples_stream import TriplesStreamEndpoint
from . graph_embeddings_stream import GraphEmbeddingsStreamEndpoint
from . triples_load import TriplesLoadEndpoint
from . graph_embeddings_load import GraphEmbeddingsLoadEndpoint

logger = logging.getLogger("api")
logger.setLevel(logging.INFO)

default_pulsar_host = os.getenv("PULSAR_HOST", "pulsar://pulsar:6650")
default_timeout = 600
default_port = 8088


class Api:

    def __init__(self, **config):

        self.app = web.Application(
            middlewares=[],
            client_max_size=256 * 1024 * 1024
        )

        self.port = int(config.get("port", default_port))
        self.timeout = int(config.get("timeout", default_timeout))
        self.pulsar_host = config.get("pulsar_host", default_pulsar_host)

        self.endpoints = [
            TextCompletionEndpoint(
                pulsar_host=self.pulsar_host, timeout=self.timeout,
            ),
            PromptEndpoint(
                pulsar_host=self.pulsar_host, timeout=self.timeout,
            ),
            GraphRagEndpoint(
                pulsar_host=self.pulsar_host, timeout=self.timeout,
            ),
            TriplesQueryEndpoint(
                pulsar_host=self.pulsar_host, timeout=self.timeout,
            ),
            EmbeddingsEndpoint(
                pulsar_host=self.pulsar_host, timeout=self.timeout,
            ),
            AgentEndpoint(
                pulsar_host=self.pulsar_host, timeout=self.timeout,
            ),
            EncyclopediaEndpoint(
                pulsar_host=self.pulsar_host, timeout=self.timeout,
            ),
            DbpediaEndpoint(
                pulsar_host=self.pulsar_host, timeout=self.timeout,
            ),
            InternetSearchEndpoint(
                pulsar_host=self.pulsar_host, timeout=self.timeout,
            ),
            TriplesStreamEndpoint(
                pulsar_host=self.pulsar_host
            ),
            GraphEmbeddingsStreamEndpoint(
                pulsar_host=self.pulsar_host
            ),
            TriplesLoadEndpoint(
                pulsar_host=self.pulsar_host
            ),
            GraphEmbeddingsLoadEndpoint(
                pulsar_host=self.pulsar_host
            ),
        ]

        # self.triples_tap = Subscriber(
        #     self.pulsar_host, triples_store_queue,
        #     "api-gateway", "api-gateway",
        #     schema=JsonSchema(Triples)
        # )

        self.triples_pub = Publisher(
            self.pulsar_host, triples_store_queue,
            schema=JsonSchema(Triples)
        )

        self.graph_embeddings_pub = Publisher(
            self.pulsar_host, graph_embeddings_store_queue,
            schema=JsonSchema(GraphEmbeddings)
        )

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

#            web.get("/api/v1/ws", self.socket),

#            web.get("/api/v1/stream/triples", self.stream_triples),

#            web.get("/api/v1/load/triples", self.load_triples),

#            web.get(
#                "/api/v1/load/graph-embeddings",
#                self.load_graph_embeddings
#            ),

        ])

    async def load_document(self, request):

        try:

            data = await request.json()

            if "metadata" in data:
                metadata = to_subgraph(data["metadata"])
            else:
                metadata = []

            # Doing a base64 decode/encode here to make sure the
            # content is valid base64
            doc = base64.b64decode(data["data"])

            resp = await self.document_out.send(
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

            resp = await self.text_out.send(
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

    async def socket(self, request):

        ws = web.WebSocketResponse()
        await ws.prepare(request)

        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                if msg.data == 'close':
                    await ws.close()
                else:
                    await ws.send_str(msg.data + '/answer')
            elif msg.type == WSMsgType.ERROR:
                print('ws connection closed with exception %s' %
                      ws.exception())

        print('websocket connection closed')

        return ws

    async def stream(self, q, ws, running, fn):

        while running.get():
            try:
                resp = await asyncio.wait_for(q.get(), 0.5)
                await ws.send_json(fn(resp))

            except TimeoutError:
                continue

            except Exception as e:
                print(f"Exception: {str(e)}", flush=True)

    async def app_factory(self):

        for ep in self.endpoints:
            await ep.start()

#        self.triples_tap_task = asyncio.create_task(
#            self.triples_tap.run()
#        )

        self.triples_pub_task = asyncio.create_task(
            self.triples_pub.run()
        )

        self.graph_embeddings_pub_task = asyncio.create_task(
            self.graph_embeddings_pub.run()
        )

        self.doc_ingest_pub_task = asyncio.create_task(self.document_out.run())

        self.text_ingest_pub_task = asyncio.create_task(self.text_out.run())

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

