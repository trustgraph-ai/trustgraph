
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
import aiopulsar
from prometheus_client import start_http_server

from ... log_level import LogLevel

from trustgraph.clients.llm_client import LlmClient
from trustgraph.clients.prompt_client import PromptClient

from ... schema import Value, Metadata, Document, TextDocument, Triple

from ... schema import TextCompletionRequest, TextCompletionResponse
from ... schema import text_completion_request_queue
from ... schema import text_completion_response_queue

from ... schema import PromptRequest, PromptResponse
from ... schema import prompt_request_queue
from ... schema import prompt_response_queue

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

from ... schema import document_ingest_queue, text_ingest_queue

logger = logging.getLogger("api")
logger.setLevel(logging.INFO)

default_pulsar_host = os.getenv("PULSAR_HOST", "pulsar://pulsar:6650")
default_timeout = 600
default_port = 8088

def to_value(x):
    return Value(value=x["v"], is_uri=x["e"])

def to_subgraph(x):
    return [
        Triple(
            s=to_value(t["s"]),
            p=to_value(t["p"]),
            o=to_value(t["o"])
        )
        for t in x
    ]

class Running:
    def __init__(self): self.running = True
    def get(self): return self.running
    def stop(self): self.running = False

class Publisher:

    def __init__(self, pulsar_host, topic, schema=None, max_size=10,
                 chunking_enabled=False):
        self.pulsar_host = pulsar_host
        self.topic = topic
        self.schema = schema
        self.q = asyncio.Queue(maxsize=max_size)
        self.chunking_enabled = chunking_enabled

    async def run(self):

        while True:

            try:
                async with aiopulsar.connect(self.pulsar_host) as client:
                    async with client.create_producer(
                            topic=self.topic,
                            schema=self.schema,
                            chunking_enabled=self.chunking_enabled,
                    ) as producer:
                        while True:
                            id, item = await self.q.get()

                            if id:
                                await producer.send(item, { "id": id })
                            else:
                                await producer.send(item)

            except Exception as e:
                print("Exception:", e, flush=True)

            # If handler drops out, sleep a retry
            await asyncio.sleep(2)

    async def send(self, id, msg):
        await self.q.put((id, msg))

class Subscriber:

    def __init__(self, pulsar_host, topic, subscription, consumer_name,
                 schema=None, max_size=10):
        self.pulsar_host = pulsar_host
        self.topic = topic
        self.subscription = subscription
        self.consumer_name = consumer_name
        self.schema = schema
        self.q = {}
        self.full = {}

    async def run(self):
        while True:
            try:
                async with aiopulsar.connect(self.pulsar_host) as client:
                    async with client.subscribe(
                        topic=self.topic,
                        subscription_name=self.subscription,
                        consumer_name=self.consumer_name,
                        schema=self.schema,
                    ) as consumer:
                        while True:
                            msg = await consumer.receive()

                            # Acknowledge successful reception of the message
                            await consumer.acknowledge(msg)

                            try:
                                id = msg.properties()["id"]
                            except:
                                id = None

                            value = msg.value()
                            if id in self.q:
                                await self.q[id].put(value)

                            for q in self.full.values():
                                await q.put(value)

            except Exception as e:
                print("Exception:", e, flush=True)
         
            # If handler drops out, sleep a retry
            await asyncio.sleep(2)

    async def subscribe(self, id):
        q = asyncio.Queue()
        self.q[id] = q
        return q

    async def unsubscribe(self, id):
        if id in self.q:
            del self.q[id]
    
    async def subscribe_all(self, id):
        q = asyncio.Queue()
        self.full[id] = q
        return q

    async def unsubscribe_all(self, id):
        if id in self.full:
            del self.full[id]

def serialize_value(v):
    return {
        "v": v.value,
        "e": v.is_uri,
    }

def serialize_triple(t):
    return {
        "s": serialize_value(t.s),
        "p": serialize_value(t.p),
        "o": serialize_value(t.o)
    }

def serialize_subgraph(sg):
    return [
        serialize_triple(t)
        for t in sg
    ]

def serialize_triples(message):
    return {
        "metadata": {
            "id": message.metadata.id,
            "metadata": serialize_subgraph(message.metadata.metadata),
            "user": message.metadata.user,
            "collection": message.metadata.collection,
        },
        "triples": serialize_subgraph(message.triples),
    }
    
def serialize_graph_embeddings(message):
    return {
        "metadata": {
            "id": message.metadata.id,
            "metadata": serialize_subgraph(message.metadata.metadata),
            "user": message.metadata.user,
            "collection": message.metadata.collection,
        },
        "vectors": message.vectors,
        "entity": message.entity,
    }
    
class Api:

    def __init__(self, **config):

        self.app = web.Application(
            middlewares=[],
            client_max_size=256 * 1024 * 1024
        )

        self.port = int(config.get("port", default_port))
        self.timeout = int(config.get("timeout", default_timeout))
        self.pulsar_host = config.get("pulsar_host", default_pulsar_host)

        self.llm_out = Publisher(
            self.pulsar_host, text_completion_request_queue,
            schema=JsonSchema(TextCompletionRequest)
        )

        self.llm_in = Subscriber(
            self.pulsar_host, text_completion_response_queue,
            "api-gateway", "api-gateway",
            JsonSchema(TextCompletionResponse)
        )

        self.prompt_out = Publisher(
            self.pulsar_host, prompt_request_queue,
            schema=JsonSchema(PromptRequest)
        )

        self.prompt_in = Subscriber(
            self.pulsar_host, prompt_response_queue,
            "api-gateway", "api-gateway",
            JsonSchema(PromptResponse)
        )

        self.graph_rag_out = Publisher(
            self.pulsar_host, graph_rag_request_queue,
            schema=JsonSchema(GraphRagQuery)
        )

        self.graph_rag_in = Subscriber(
            self.pulsar_host, graph_rag_response_queue,
            "api-gateway", "api-gateway",
            JsonSchema(GraphRagResponse)
        )

        self.triples_query_out = Publisher(
            self.pulsar_host, triples_request_queue,
            schema=JsonSchema(TriplesQueryRequest)
        )

        self.triples_query_in = Subscriber(
            self.pulsar_host, triples_response_queue,
            "api-gateway", "api-gateway",
            JsonSchema(TriplesQueryResponse)
        )

        self.agent_out = Publisher(
            self.pulsar_host, agent_request_queue,
            schema=JsonSchema(AgentRequest)
        )

        self.agent_in = Subscriber(
            self.pulsar_host, agent_response_queue,
            "api-gateway", "api-gateway",
            JsonSchema(AgentResponse)
        )

        self.embeddings_out = Publisher(
            self.pulsar_host, embeddings_request_queue,
            schema=JsonSchema(EmbeddingsRequest)
        )

        self.embeddings_in = Subscriber(
            self.pulsar_host, embeddings_response_queue,
            "api-gateway", "api-gateway",
            JsonSchema(EmbeddingsResponse)
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

        self.encyclopedia_lookup_out = Publisher(
            self.pulsar_host, encyclopedia_lookup_request_queue,
            schema=JsonSchema(LookupRequest)
        )

        self.encyclopedia_lookup_in = Subscriber(
            self.pulsar_host, encyclopedia_lookup_response_queue,
            "api-gateway", "api-gateway",
            JsonSchema(LookupResponse)
        )

        self.app.add_routes([
            web.post("/api/v1/text-completion", self.llm),
            web.post("/api/v1/prompt", self.prompt),
            web.post("/api/v1/graph-rag", self.graph_rag),
            web.post("/api/v1/triples-query", self.triples_query),
            web.post("/api/v1/agent", self.agent),
            web.post("/api/v1/encyclopedia", self.encyclopedia),
            web.post("/api/v1/embeddings", self.embeddings),
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

    async def llm(self, request):

        id = str(uuid.uuid4())

        try:

            data = await request.json()

            q = await self.llm_in.subscribe(id)

            await self.llm_out.send(
                id,
                TextCompletionRequest(
                    system=data["system"],
                    prompt=data["prompt"]
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
                { "response": resp.response }
            )

        except Exception as e:
            logging.error(f"Exception: {e}")

            return web.json_response(
                { "error": str(e) }
            )

        finally:
            await self.llm_in.unsubscribe(id)

    async def prompt(self, request):

        id = str(uuid.uuid4())

        try:

            data = await request.json()

            q = await self.prompt_in.subscribe(id)

            terms = {
                k: json.dumps(v)
                for k, v in data["variables"].items()
            }

            await self.prompt_out.send(
                id,
                PromptRequest(
                    id=data["id"],
                    terms=terms
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

            if resp.object:
                return web.json_response(
                    { "object": resp.object }
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
            await self.prompt_in.unsubscribe(id)

    async def graph_rag(self, request):

        id = str(uuid.uuid4())

        try:

            data = await request.json()

            q = await self.graph_rag_in.subscribe(id)

            await self.graph_rag_out.send(
                id,
                GraphRagQuery(
                    query=data["query"],
                    user=data.get("user", "trustgraph"),
                    collection=data.get("collection", "default"),
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
                { "response": resp.response }
            )

        except Exception as e:
            logging.error(f"Exception: {e}")

            return web.json_response(
                { "error": str(e) }
            )

        finally:
            await self.graph_rag_in.unsubscribe(id)

    async def triples_query(self, request):

        id = str(uuid.uuid4())

        try:

            data = await request.json()

            q = await self.triples_query_in.subscribe(id)

            if "s" in data:
                s = to_value(data["s"])
            else:
                s = None

            if "p" in data:
                p = to_value(data["p"])
            else:
                p = None

            if "o" in data:
                o = to_value(data["o"])
            else:
                o = None

            limit = int(data.get("limit", 10000))

            await self.triples_query_out.send(
                id,
                TriplesQueryRequest(
                    s = s, p = p, o = o,
                    limit = limit,
                    user = data.get("user", "trustgraph"),
                    collection = data.get("collection", "default"),
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
                {
                    "response": serialize_subgraph(resp.triples),
                }
            )

        except Exception as e:
            logging.error(f"Exception: {e}")

            return web.json_response(
                { "error": str(e) }
            )

        finally:
            await self.graph_rag_in.unsubscribe(id)

    async def agent(self, request):

        id = str(uuid.uuid4())

        try:

            data = await request.json()

            q = await self.agent_in.subscribe(id)

            await self.agent_out.send(
                id,
                AgentRequest(
                    question=data["question"],
                )
            )

            while True:
                try:
                    resp = await asyncio.wait_for(q.get(), self.timeout)
                except:
                    raise RuntimeError("Timeout waiting for response")

                if resp.error:
                    return web.json_response(
                        { "error": resp.error.message }
                    )

                if resp.answer: break

                if resp.thought: print("thought:", resp.thought)
                if resp.observation: print("observation:", resp.observation)

            if resp.answer:
                return web.json_response(
                    { "answer": resp.answer }
                )

            # Can't happen, ook at the logic
            raise RuntimeError("Strange state")

        except Exception as e:
            logging.error(f"Exception: {e}")

            return web.json_response(
                { "error": str(e) }
            )

        finally:
            await self.agent_in.unsubscribe(id)

    async def embeddings(self, request):

        id = str(uuid.uuid4())

        try:

            data = await request.json()

            q = await self.embeddings_in.subscribe(id)

            await self.embeddings_out.send(
                id,
                EmbeddingsRequest(
                    text=data["text"],
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
                { "vectors": resp.vectors }
            )

        except Exception as e:
            logging.error(f"Exception: {e}")

            return web.json_response(
                { "error": str(e) }
            )

        finally:
            await self.embeddings_in.unsubscribe(id)

    async def encyclopedia(self, request):

        id = str(uuid.uuid4())

        try:

            data = await request.json()

            print(data)

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

        self.llm_pub_task = asyncio.create_task(self.llm_in.run())
        self.llm_sub_task = asyncio.create_task(self.llm_out.run())

        self.prompt_pub_task = asyncio.create_task(self.prompt_in.run())
        self.prompt_sub_task = asyncio.create_task(self.prompt_out.run())

        self.graph_rag_pub_task = asyncio.create_task(self.graph_rag_in.run())
        self.graph_rag_sub_task = asyncio.create_task(self.graph_rag_out.run())

        self.triples_query_pub_task = asyncio.create_task(
            self.triples_query_in.run()
        )
        self.triples_query_sub_task = asyncio.create_task(
            self.triples_query_out.run()
        )

        self.agent_pub_task = asyncio.create_task(self.agent_in.run())
        self.agent_sub_task = asyncio.create_task(self.agent_out.run())

        self.embeddings_pub_task = asyncio.create_task(
            self.embeddings_in.run()
        )
        self.embeddings_sub_task = asyncio.create_task(
            self.embeddings_out.run()
        )

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

        self.encyclopedia_pub_task = asyncio.create_task(
            self.encyclopedia_lookup_out.run()
        )
        self.encyclopedia_sub_task = asyncio.create_task(
            self.encyclopedia_lookup_in.run()
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

