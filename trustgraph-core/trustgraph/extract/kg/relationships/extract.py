
"""
Simple decoder, accepts vector+text chunks input, applies entity
relationship analysis to get entity relationship edges which are output as
graph edges.
"""

import urllib.parse
import os
from pulsar.schema import JsonSchema

from .... schema import ChunkEmbeddings, Triple, GraphEmbeddings, Source, Value
from .... schema import chunk_embeddings_ingest_queue, triples_store_queue
from .... schema import graph_embeddings_store_queue
from .... schema import prompt_request_queue
from .... schema import prompt_response_queue
from .... log_level import LogLevel
from .... clients.prompt_client import PromptClient
from .... rdf import RDF_LABEL, TRUSTGRAPH_ENTITIES
from .... base import ConsumerProducer

RDF_LABEL_VALUE = Value(value=RDF_LABEL, is_uri=True)

module = ".".join(__name__.split(".")[1:-1])

default_input_queue = chunk_embeddings_ingest_queue
default_output_queue = triples_store_queue
default_vector_queue = graph_embeddings_store_queue
default_subscriber = module

class Processor(ConsumerProducer):

    def __init__(self, **params):

        input_queue = params.get("input_queue", default_input_queue)
        output_queue = params.get("output_queue", default_output_queue)
        vector_queue = params.get("vector_queue", default_vector_queue)
        subscriber = params.get("subscriber", default_subscriber)
        pr_request_queue = params.get(
            "prompt_request_queue", prompt_request_queue
        )
        pr_response_queue = params.get(
            "prompt_response_queue", prompt_response_queue
        )

        super(Processor, self).__init__(
            **params | {
                "input_queue": input_queue,
                "output_queue": output_queue,
                "subscriber": subscriber,
                "input_schema": ChunkEmbeddings,
                "output_schema": Triple,
                "prompt_request_queue": pr_request_queue,
                "prompt_response_queue": pr_response_queue,
            }
        )

        self.vec_prod = self.client.create_producer(
            topic=vector_queue,
            schema=JsonSchema(GraphEmbeddings),
        )

        __class__.pubsub_metric.info({
            "input_queue": input_queue,
            "output_queue": output_queue,
            "vector_queue": vector_queue,
            "prompt_request_queue": pr_request_queue,
            "prompt_response_queue": pr_response_queue,
            "subscriber": subscriber,
            "input_schema": ChunkEmbeddings.__name__,
            "output_schema": Triple.__name__,
            "vector_schema": GraphEmbeddings.__name__,
        })

        self.prompt = PromptClient(
            pulsar_host=self.pulsar_host,
            input_queue=pr_request_queue,
            output_queue=pr_response_queue,
            subscriber = module + "-prompt",
        )

    def to_uri(self, text):

        part = text.replace(" ", "-").lower().encode("utf-8")
        quoted = urllib.parse.quote(part)
        uri = TRUSTGRAPH_ENTITIES + quoted

        return uri

    def get_relationships(self, chunk):

        return self.prompt.request_relationships(chunk)

    def emit_edge(self, s, p, o):

        t = Triple(s=s, p=p, o=o)
        self.producer.send(t)

    def emit_vec(self, ent, vec):

        r = GraphEmbeddings(entity=ent, vectors=vec)
        self.vec_prod.send(r)

    def handle(self, msg):

        v = msg.value()
        print(f"Indexing {v.source.id}...", flush=True)

        chunk = v.chunk.decode("utf-8")

        try:

            rels = self.get_relationships(chunk)

            for rel in rels:

                s = rel.s
                p = rel.p
                o = rel.o

                if s == "": continue
                if p == "": continue
                if o == "": continue

                if s is None: continue
                if p is None: continue
                if o is None: continue

                s_uri = self.to_uri(s)
                s_value = Value(value=str(s_uri), is_uri=True)

                p_uri = self.to_uri(p)
                p_value = Value(value=str(p_uri), is_uri=True)

                if rel.o_entity: 
                    o_uri = self.to_uri(o)
                    o_value = Value(value=str(o_uri), is_uri=True)
                else:
                    o_value = Value(value=str(o), is_uri=False)

                self.emit_edge(
                    s_value,
                    p_value,
                    o_value
                )

                # Label for s
                self.emit_edge(
                    s_value,
                    RDF_LABEL_VALUE,
                    Value(value=str(s), is_uri=False)
                )

                # Label for p
                self.emit_edge(
                    p_value,
                    RDF_LABEL_VALUE,
                    Value(value=str(p), is_uri=False)
                )

                if rel.o_entity:
                    # Label for o
                    self.emit_edge(
                        o_value,
                        RDF_LABEL_VALUE,
                        Value(value=str(o), is_uri=False)
                    )

                self.emit_vec(s_value, v.vectors)
                self.emit_vec(p_value, v.vectors)
                if rel.o_entity:
                    self.emit_vec(o_value, v.vectors)

        except Exception as e:
            print("Exception: ", e, flush=True)

        print("Done.", flush=True)

    @staticmethod
    def add_args(parser):

        ConsumerProducer.add_args(
            parser, default_input_queue, default_subscriber,
            default_output_queue,
        )

        parser.add_argument(
            '-c', '--vector-queue',
            default=default_vector_queue,
            help=f'Vector output queue (default: {default_vector_queue})'
        )

        parser.add_argument(
            '--prompt-request-queue',
            default=prompt_request_queue,
            help=f'Prompt request queue (default: {prompt_request_queue})',
        )

        parser.add_argument(
            '--prompt-response-queue',
            default=prompt_response_queue,
            help=f'Prompt response queue (default: {prompt_response_queue})',
        )

def run():

    Processor.start(module, __doc__)
