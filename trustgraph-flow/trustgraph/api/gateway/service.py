
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
import json
import logging
import uuid
import os

import pulsar
from pulsar.asyncio import Client
from pulsar.schema import JsonSchema
import _pulsar
import aiopulsar
from prometheus_client import start_http_server

from ... log_level import LogLevel

from trustgraph.clients.llm_client import LlmClient
from trustgraph.clients.prompt_client import PromptClient

from ... schema import TextCompletionRequest, TextCompletionResponse
from ... schema import text_completion_request_queue
from ... schema import text_completion_response_queue

from ... schema import PromptRequest, PromptResponse
from ... schema import prompt_request_queue
from ... schema import prompt_response_queue

from ... schema import GraphRagQuery, GraphRagResponse
from ... schema import graph_rag_request_queue
from ... schema import graph_rag_response_queue

from ... schema import TriplesQueryRequest, TriplesQueryResponse, Value
from ... schema import triples_request_queue
from ... schema import triples_response_queue

from ... schema import AgentRequest, AgentResponse
from ... schema import agent_request_queue
from ... schema import agent_response_queue

from ... schema import EmbeddingsRequest, EmbeddingsResponse
from ... schema import embeddings_request_queue
from ... schema import embeddings_response_queue

logger = logging.getLogger("api")
logger.setLevel(logging.INFO)

default_pulsar_host = os.getenv("PULSAR_HOST", "pulsar://pulsar:6650")
default_timeout = 600
default_port = 8088

class Publisher:

    def __init__(self, pulsar_host, topic, schema=None, max_size=10):
        self.pulsar_host = pulsar_host
        self.topic = topic
        self.schema = schema
        self.q = asyncio.Queue(maxsize=max_size)

    async def run(self):

        while True:

            try:
                async with aiopulsar.connect(self.pulsar_host) as client:
                    async with client.create_producer(
                            topic=self.topic,
                            schema=self.schema,
                    ) as producer:
                        while True:
                            id, item = await self.q.get()
                            await producer.send(item, { "id": id })
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
                            id = msg.properties()["id"]
                            value = msg.value()
                            if id in self.q:
                                await self.q[id].put(value)
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
    
class Api:

    def __init__(self, **config):

        self.app = web.Application(middlewares=[])

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

        self.app.add_routes([
            web.post("/api/v1/text-completion", self.llm),
            web.post("/api/v1/prompt", self.prompt),
            web.post("/api/v1/graph-rag", self.graph_rag),
            web.post("/api/v1/triples-query", self.triples_query),
            web.post("/api/v1/agent", self.agent),
            web.post("/api/v1/embeddings", self.embeddings),
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
                if data["s"].startswith("http:") or data["s"].startswith("https:"):
                    s = Value(value=data["s"], is_uri=True)
                else:
                    s = Value(value=data["s"], is_uri=True)
            else:
                s = None

            if "p" in data:
                if data["p"].startswith("http:") or data["p"].startswith("https:"):
                    p = Value(value=data["p"], is_uri=True)
                else:
                    p = Value(value=data["p"], is_uri=True)
            else:
                p = None

            if "o" in data:
                if data["o"].startswith("http:") or data["o"].startswith("https:"):
                    o = Value(value=data["o"], is_uri=True)
                else:
                    o = Value(value=data["o"], is_uri=True)
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
                    "response": [
                        {
                            "s": {
                                "v": t.s.value,
                                "e": t.s.is_uri,
                            },
                            "p": {
                                "v": t.p.value,
                                "e": t.p.is_uri,
                            },
                            "o": {
                                "v": t.o.value,
                                "e": t.o.is_uri,
                            }
                        }
                        for t in resp.triples
                    ]
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
