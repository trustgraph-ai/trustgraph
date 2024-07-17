
"""
Simple decoder, accepts vector+text chunks input, applies entity analysis to
get entity definitions which are output as graph edges.
"""

from ... schema import VectorsChunk, Triple, Source, Value
from ... log_level import LogLevel
from ... llm_client import LlmClient
from ... prompts import to_definitions
from ... rdf import TRUSTGRAPH_ENTITIES, DEFINITION
from ... base import ConsumerProducer

DEFINITION_VALUE = Value(value=DEFINITION, is_uri=True)

default_input_queue = 'vectors-chunk-load'
default_output_queue = 'graph-load'
default_subscriber = 'kg-extract-definitions'

class Processor(ConsumerProducer):

    def __init__(
            self,
            pulsar_host=None,
            input_queue=default_input_queue,
            output_queue=default_output_queue,
            subscriber=default_subscriber,
            log_level=LogLevel.INFO,
    ):

        super(Processor, self).__init__(
            pulsar_host=pulsar_host,
            log_level=log_level,
            input_queue=input_queue,
            output_queue=output_queue,
            subscriber=subscriber,
            input_schema=VectorsChunk,
            output_schema=Triple,
        )

        self.llm = LlmClient(pulsar_host=pulsar_host)

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

def run():

    Processor.start("kg-extract-definitions", __doc__)

