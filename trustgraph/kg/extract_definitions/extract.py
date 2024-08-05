
"""
Simple decoder, accepts embeddings+text chunks input, applies entity analysis to
get entity definitions which are output as graph edges.
"""

import urllib.parse
import json

from ... schema import ChunkEmbeddings, Triple, Source, Value
from ... schema import chunk_embeddings_ingest_queue, triples_store_queue
from ... schema import text_completion_request_queue
from ... schema import text_completion_response_queue
from ... log_level import LogLevel
from ... llm_client import LlmClient
from ... prompts import to_definitions
from ... rdf import TRUSTGRAPH_ENTITIES, DEFINITION
from ... base import ConsumerProducer

DEFINITION_VALUE = Value(value=DEFINITION, is_uri=True)

module = ".".join(__name__.split(".")[1:-1])

default_input_queue = chunk_embeddings_ingest_queue
default_output_queue = triples_store_queue
default_subscriber = module

class Processor(ConsumerProducer):

    def __init__(self, **params):

        input_queue = params.get("input_queue", default_input_queue)
        output_queue = params.get("output_queue", default_output_queue)
        subscriber = params.get("subscriber", default_subscriber)
        tc_request_queue = params.get(
            "text_completion_request_queue", text_completion_request_queue
        )
        tc_response_queue = params.get(
            "text_completion_response_queue", text_completion_response_queue
        )

        super(Processor, self).__init__(
            **params | {
                "input_queue": input_queue,
                "output_queue": output_queue,
                "subscriber": subscriber,
                "input_schema": ChunkEmbeddings,
                "output_schema": Triple,
                "text_completion_request_queue": tc_request_queue,
                "text_completion_response_queue": tc_response_queue,
            }
        )

        self.llm = LlmClient(
            pulsar_host=self.pulsar_host,
            input_queue=tc_request_queue,
            output_queue=tc_response_queue,
            subscriber = module + "-llm",
        )

    def to_uri(self, text):

        part = text.replace(" ", "-").lower().encode("utf-8")
        quoted = urllib.parse.quote(part)
        uri = TRUSTGRAPH_ENTITIES + quoted

        return uri

    def get_definitions(self, chunk):

        prompt = to_definitions(chunk)
        resp = self.llm.request(prompt)

        defs = json.loads(resp)

        return defs

    def emit_edge(self, s, p, o):

        t = Triple(s=s, p=p, o=o)
        self.producer.send(t)

    def handle(self, msg):

        v = msg.value()
        print(f"Indexing {v.source.id}...", flush=True)

        chunk = v.chunk.decode("utf-8")

        try:

            defs = self.get_definitions(chunk)
            print(json.dumps(defs, indent=4), flush=True)

            for defn in defs:

                s = defn["entity"]
                s_uri = self.to_uri(s)

                o = defn["definition"]

                if s == "": continue
                if o == "": continue

                s_value = Value(value=str(s_uri), is_uri=True)
                o_value = Value(value=str(o), is_uri=False)

                self.emit_edge(s_value, DEFINITION_VALUE, o_value)

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
            '--text-completion-request-queue',
            default=text_completion_request_queue,
            help=f'Text completion request queue (default: {text_completion_request_queue})',
        )

        parser.add_argument(
            '--text-completion-response-queue',
            default=text_completion_response_queue,
            help=f'Text completion response queue (default: {text_completion_response_queue})',
        )

def run():

    Processor.start(module, __doc__)

