
"""
Simple decoder, accepts text chunks input, applies entity analysis to
get topics which are output as graph edges.
"""

import urllib.parse
import json
import logging

# Module logger
logger = logging.getLogger(__name__)

from .... schema import Chunk, Triple, Triples, Metadata, Term, IRI, LITERAL
from .... schema import chunk_ingest_queue, triples_store_queue
from .... schema import prompt_request_queue
from .... schema import prompt_response_queue
from .... log_level import LogLevel
from .... clients.prompt_client import PromptClient
from .... rdf import TRUSTGRAPH_ENTITIES, DEFINITION
from .... base import ConsumerProducer

DEFINITION_VALUE = Term(type=IRI, iri=DEFINITION)

module = "kg-extract-topics"

default_input_queue = chunk_ingest_queue
default_output_queue = triples_store_queue
default_subscriber = module

class Processor(ConsumerProducer):

    def __init__(self, **params):

        input_queue = params.get("input_queue", default_input_queue)
        output_queue = params.get("output_queue", default_output_queue)
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
                "input_schema": Chunk,
                "output_schema": Triples,
                "prompt_request_queue": pr_request_queue,
                "prompt_response_queue": pr_response_queue,
            }
        )

        self.prompt = PromptClient(
            pulsar_host=self.pulsar_host,
            pulsar_api_key=self.pulsar_api_key,
            input_queue=pr_request_queue,
            output_queue=pr_response_queue,
            subscriber = module + "-prompt",
        )

    def to_uri(self, text):

        part = text.replace(" ", "-").lower().encode("utf-8")
        quoted = urllib.parse.quote(part)
        uri = TRUSTGRAPH_ENTITIES + quoted

        return uri

    def get_topics(self, chunk):

        return self.prompt.request_topics(chunk)

    async def emit_edge(self, metadata, s, p, o):

        t = Triples(
            metadata=metadata,
            triples=[Triple(s=s, p=p, o=o)],
        )
        await self.send(t)

    async def handle(self, msg):

        v = msg.value()
        logger.info(f"Extracting topics from {v.metadata.id}...")

        chunk = v.chunk.decode("utf-8")

        try:

            defs = self.get_topics(chunk)

            for defn in defs:

                s = defn.name
                o = defn.definition

                if s == "": continue
                if o == "": continue

                if s is None: continue
                if o is None: continue

                s_uri = self.to_uri(s)

                s_value = Term(type=IRI, iri=str(s_uri))
                o_value = Term(type=LITERAL, value=str(o))

                await self.emit_edge(
                    v.metadata, s_value, DEFINITION_VALUE, o_value
                )

        except Exception as e:
            logger.error(f"Topic extraction exception: {e}", exc_info=True)

        logger.debug("Topic extraction complete")

    @staticmethod
    def add_args(parser):

        ConsumerProducer.add_args(
            parser, default_input_queue, default_subscriber,
            default_output_queue,
        )

        parser.add_argument(
            '--prompt-request-queue',
            default=prompt_request_queue,
            help=f'Prompt request queue (default: {prompt_request_queue})',
        )

        parser.add_argument(
            '--prompt-completion-response-queue',
            default=prompt_response_queue,
            help=f'Prompt response queue (default: {prompt_response_queue})',
        )

def run():

    Processor.launch(module, __doc__)

