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

from trustgraph.clients.llm_client import LlmClient
from trustgraph.clients.prompt_client import PromptClient

from ... schema import Value, Metadata, Document, TextDocument, Triple

from ... schema import GraphRagQuery, GraphRagResponse
from ... schema import graph_rag_request_queue
from ... schema import graph_rag_response_queue

from ... schema import TriplesQueryRequest, TriplesQueryResponse, Triples
from ... schema import triples_request_queue
from ... schema import triples_response_queue
from ... schema import triples_store_queue

from ... schema import GraphEmbeddings
from ... schema import graph_embeddings_store_queue

from ... schema import AgentRequest, AgentResponse
from ... schema import agent_request_queue
from ... schema import agent_response_queue

from ... schema import EmbeddingsRequest, EmbeddingsResponse
from ... schema import embeddings_request_queue
from ... schema import embeddings_response_queue

from ... schema import LookupRequest, LookupResponse
from ... schema import encyclopedia_lookup_request_queue
from ... schema import encyclopedia_lookup_response_queue
from ... schema import internet_search_request_queue
from ... schema import internet_search_response_queue
from ... schema import dbpedia_lookup_request_queue
from ... schema import dbpedia_lookup_response_queue

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

logger = logging.getLogger("api")
logger.setLevel(logging.INFO)

default_pulsar_host = os.getenv("PULSAR_HOST", "pulsar://pulsar:6650")
default_timeout = 600
default_port = 8088

class GraphRagEndpoint(ServiceEndpoint):
    def __init__(self, pulsar_host, timeout):

        super(GraphRagEndpoint, self).__init__(
            pulsar_host=pulsar_host,
            request_queue=graph_rag_request_queue,
            response_queue=graph_rag_response_queue,
            request_schema=GraphRagQuery,
            response_schema=GraphRagResponse,
            endpoint_path="/api/v1/graph-rag",
            timeout=timeout,
        )

    def to_request(self, body):
        return GraphRagQuery(
            query=body["query"],
            user=body.get("user", "trustgraph"),
            collection=body.get("collection", "default"),
        )

    def from_response(self, message):
        return { "response": message.response }

class TriplesQueryEndpoint(ServiceEndpoint):
    def __init__(self, pulsar_host, timeout):

        super(TriplesQueryEndpoint, self).__init__(
            pulsar_host=pulsar_host,
            request_queue=triples_request_queue,
            response_queue=triples_response_queue,
            request_schema=TriplesQueryRequest,
            response_schema=TriplesQueryResponse,
            endpoint_path="/api/v1/triples-query",
            timeout=timeout,
        )

    def to_request(self, body):

        if "s" in body:
            s = to_value(body["s"])
        else:
            s = None

        if "p" in body:
            p = to_value(body["p"])
        else:
            p = None

        if "o" in body:
            o = to_value(body["o"])
        else:
            o = None

        limit = int(body.get("limit", 10000))

        return TriplesQueryRequest(
            s = s, p = p, o = o,
            limit = limit,
            user = body.get("user", "trustgraph"),
            collection = body.get("collection", "default"),
        )

    def from_response(self, message):
        print(message)
        return {
            "response": serialize_subgraph(message.triples)
        }

class EmbeddingsEndpoint(ServiceEndpoint):
    def __init__(self, pulsar_host, timeout):

        super(EmbeddingsEndpoint, self).__init__(
            pulsar_host=pulsar_host,
            request_queue=embeddings_request_queue,
            response_queue=embeddings_response_queue,
            request_schema=EmbeddingsRequest,
            response_schema=EmbeddingsResponse,
            endpoint_path="/api/v1/embeddings",
            timeout=timeout,
        )

    def to_request(self, body):
        return EmbeddingsRequest(
            text=body["text"]
        )

    def from_response(self, message):
        return { "vectors": message.vectors }

class AgentEndpoint(MultiResponseServiceEndpoint):
    def __init__(self, pulsar_host, timeout):

        super(AgentEndpoint, self).__init__(
            pulsar_host=pulsar_host,
            request_queue=agent_request_queue,
            response_queue=agent_response_queue,
            request_schema=AgentRequest,
            response_schema=AgentResponse,
            endpoint_path="/api/v1/agent",
            timeout=timeout,
        )

    def to_request(self, body):
        return AgentRequest(
            question=body["question"]
        )

    def from_response(self, message):
        if message.answer:
            return { "answer": message.answer }, True
        else:
            return {}, False

class EncyclopediaEndpoint(ServiceEndpoint):
    def __init__(self, pulsar_host, timeout):

        super(EncyclopediaEndpoint, self).__init__(
            pulsar_host=pulsar_host,
            request_queue=encyclopedia_lookup_request_queue,
            response_queue=encyclopedia_lookup_response_queue,
            request_schema=LookupRequest,
            response_schema=LookupResponse,
            endpoint_path="/api/v1/encyclopedia",
            timeout=timeout,
        )

    def to_request(self, body):
        return LookupRequest(
            term=body["term"],
            kind=body.get("kind", None),
        )

    def from_response(self, message):
        return { "text": message.text }

class Api:

    def __init__(self, **config):

        self.app = web.Application(
            middlewares=[],
            client_max_size=256 * 1024 * 1024
        )

        self.port = int(config.get("port", default_port))
        self.timeout = int(config.get("timeout", default_timeout))
        self.pulsar_host = config.get("pulsar_host", default_pulsar_host)

        self.text_completion = TextCompletionEndpoint(
            pulsar_host=self.pulsar_host, timeout=self.timeout,
        )

        self.prompt = PromptEndpoint(
            pulsar_host=self.pulsar_host, timeout=self.timeout,
        )

        self.graph_rag = GraphRagEndpoint(
            pulsar_host=self.pulsar_host, timeout=self.timeout,
        )

        self.triples_query = TriplesQueryEndpoint(
            pulsar_host=self.pulsar_host, timeout=self.timeout,
        )

        self.embeddings = EmbeddingsEndpoint(
            pulsar_host=self.pulsar_host, timeout=self.timeout,
        )

        self.agent = AgentEndpoint(
            pulsar_host=self.pulsar_host, timeout=self.timeout,
        )

        self.encyclopedia = EncyclopediaEndpoint(
            pulsar_host=self.pulsar_host, timeout=self.timeout,
        )




        self.triples_tap = Subscriber(
            self.pulsar_host, triples_store_queue,
            "api-gateway", "api-gateway",
            schema=JsonSchema(Triples)
        )

        self.triples_pub = Publisher(
            self.pulsar_host, triples_store_queue,
            schema=JsonSchema(Triples)
        )

        self.graph_embeddings_tap = Subscriber(
            self.pulsar_host, graph_embeddings_store_queue,
            "api-gateway", "api-gateway",
            schema=JsonSchema(GraphEmbeddings)
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


        self.internet_search_out = Publisher(
            self.pulsar_host, internet_search_request_queue,
            schema=JsonSchema(LookupRequest)
        )

        self.internet_search_in = Subscriber(
            self.pulsar_host, internet_search_response_queue,
            "api-gateway", "api-gateway",
            JsonSchema(LookupResponse)
        )

        self.dbpedia_lookup_out = Publisher(
            self.pulsar_host, dbpedia_lookup_request_queue,
            schema=JsonSchema(LookupRequest)
        )

        self.dbpedia_lookup_in = Subscriber(
            self.pulsar_host, dbpedia_lookup_response_queue,
            "api-gateway", "api-gateway",
            JsonSchema(LookupResponse)
        )

        self.text_completion.add_routes(self.app)
        self.prompt.add_routes(self.app)
        self.graph_rag.add_routes(self.app)
        self.triples_query.add_routes(self.app)
        self.embeddings.add_routes(self.app)
        self.agent.add_routes(self.app)
        self.encyclopedia.add_routes(self.app)

        self.app.add_routes([
#            web.post("/api/v1/triples-query", self.triples_query),
#            web.post("/api/v1/internet-search", self.internet-search),
#            web.post("/api/v1/dbpedia", self.dbpedia),
            web.post("/api/v1/load/document", self.load_document),
            web.post("/api/v1/load/text", self.load_text),
            web.get("/api/v1/ws", self.socket),

            web.get("/api/v1/stream/triples", self.stream_triples),
            web.get(
                "/api/v1/stream/graph-embeddings",
                self.stream_graph_embeddings
            ),

            web.get("/api/v1/load/triples", self.load_triples),
            web.get(
                "/api/v1/load/graph-embeddings",
                self.load_graph_embeddings
            ),

        ])

    async def encyclopedia(self, request):

        id = str(uuid.uuid4())

        try:

            data = await request.json()

            q = await self.encyclopedia_lookup_in.subscribe(id)

            await self.encyclopedia_lookup_out.send(
                id,
                LookupRequest(
                    term=data["term"],
                    kind=data.get("kind", None),
                )
            )

            try:
                resp = await asyncio.wait_for(q.get(), self.timeout)
            except:
                raise RuntimeError("Timeout waiting for response")

            if resp.error:
                return web.json_response(
                    { "error": resp.error.message }
                )

            return web.json_response(
                { "text": resp.text }
            )

        except Exception as e:
            logging.error(f"Exception: {e}")

            return web.json_response(
                { "error": str(e) }
            )

        finally:
            await self.encyclopedia_lookup_in.unsubscribe(id)

    async def internet_search(self, request):

        id = str(uuid.uuid4())

        try:

            data = await request.json()

            q = await self.internet_search_in.subscribe(id)

            await self.internet_search_out.send(
                id,
                LookupRequest(
                    term=data["term"],
                    kind=data.get("kind", None),
                )
            )

            try:
                resp = await asyncio.wait_for(q.get(), self.timeout)
            except:
                raise RuntimeError("Timeout waiting for response")

            if resp.error:
                return web.json_response(
                    { "error": resp.error.message }
                )

            return web.json_response(
                { "text": resp.text }
            )

        except Exception as e:
            logging.error(f"Exception: {e}")

            return web.json_response(
                { "error": str(e) }
            )

        finally:
            await self.internet_search_in.unsubscribe(id)

    async def dbpedia(self, request):

        id = str(uuid.uuid4())

        try:

            data = await request.json()

            q = await self.dbpedia_lookup_in.subscribe(id)

            await self.dbpedia_lookup_out.send(
                id,
                LookupRequest(
                    term=data["term"],
                    kind=data.get("kind", None),
                )
            )

            try:
                resp = await asyncio.wait_for(q.get(), self.timeout)
            except:
                raise RuntimeError("Timeout waiting for response")

            if resp.error:
                return web.json_response(
                    { "error": resp.error.message }
                )

            return web.json_response(
                { "text": resp.text }
            )

        except Exception as e:
            logging.error(f"Exception: {e}")

            return web.json_response(
                { "error": str(e) }
            )

        finally:
            await self.dbpedia_lookup_in.unsubscribe(id)

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

    async def stream_triples(self, request):

        id = str(uuid.uuid4())

        q = await self.triples_tap.subscribe_all(id)
        running = Running()

        ws = web.WebSocketResponse()
        await ws.prepare(request)

        tsk = asyncio.create_task(self.stream(
            q,
            ws,
            running,
            serialize_triples,
        ))

        async for msg in ws:
            if msg.type == WSMsgType.ERROR:
                break
            else:
                # Ignore incoming messages
                pass

        running.stop()

        await self.triples_tap.unsubscribe_all(id)
        await tsk

        return ws

    async def stream_graph_embeddings(self, request):

        id = str(uuid.uuid4())

        q = await self.graph_embeddings_tap.subscribe_all(id)
        running = Running()

        ws = web.WebSocketResponse()
        await ws.prepare(request)

        tsk = asyncio.create_task(self.stream(
            q,
            ws,
            running,
            serialize_graph_embeddings,
        ))

        async for msg in ws:
            if msg.type == WSMsgType.ERROR:
                break
            else:
                # Ignore incoming messages
                pass

        running.stop()

        await self.graph_embeddings_tap.unsubscribe_all(id)
        await tsk

        return ws

    async def load_triples(self, request):

        ws = web.WebSocketResponse()
        await ws.prepare(request)

        async for msg in ws:

            try:

                if msg.type == WSMsgType.TEXT:

                    data = msg.json()

                    elt = Triples(
                        metadata=Metadata(
                            id=data["metadata"]["id"],
                            metadata=to_subgraph(data["metadata"]["metadata"]),
                            user=data["metadata"]["user"],
                            collection=data["metadata"]["collection"],
                        ),
                        triples=to_subgraph(data["triples"]),
                    )

                    await self.triples_pub.send(None, elt)

                elif msg.type == WSMsgType.ERROR:
                    break

            except Exception as e:

                print("Exception:", e)

        return ws

    async def load_graph_embeddings(self, request):

        ws = web.WebSocketResponse()
        await ws.prepare(request)

        async for msg in ws:

            try:

                if msg.type == WSMsgType.TEXT:

                    data = msg.json()

                    elt = GraphEmbeddings(
                        metadata=Metadata(
                            id=data["metadata"]["id"],
                            metadata=to_subgraph(data["metadata"]["metadata"]),
                            user=data["metadata"]["user"],
                            collection=data["metadata"]["collection"],
                        ),
                        entity=to_value(data["entity"]),
                        vectors=data["vectors"],
                    )

                    await self.graph_embeddings_pub.send(None, elt)

                elif msg.type == WSMsgType.ERROR:
                    break

            except Exception as e:

                print("Exception:", e)

        return ws

    async def app_factory(self):

        await self.text_completion.start()
        await self.prompt.start()
        await self.graph_rag.start()
        await self.triples_query.start()
        await self.embeddings.start()
        await self.agent.start()
        await self.encyclopedia.start()

        self.triples_tap_task = asyncio.create_task(
            self.triples_tap.run()
        )

        self.triples_pub_task = asyncio.create_task(
            self.triples_pub.run()
        )

        self.graph_embeddings_tap_task = asyncio.create_task(
            self.graph_embeddings_tap.run()
        )

        self.graph_embeddings_pub_task = asyncio.create_task(
            self.graph_embeddings_pub.run()
        )

        self.doc_ingest_pub_task = asyncio.create_task(self.document_out.run())

        self.text_ingest_pub_task = asyncio.create_task(self.text_out.run())

        self.search_pub_task = asyncio.create_task(
            self.internet_search_out.run()
        )
        self.search_sub_task = asyncio.create_task(
            self.internet_search_in.run()
        )

        self.dbpedia_pub_task = asyncio.create_task(
            self.dbpedia_lookup_out.run()
        )
        self.dbpedia_sub_task = asyncio.create_task(
            self.dbpedia_lookup_in.run()
        )

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

