
"""
Simple decoder, accepts PDF documents on input, outputs pages from the
PDF document as text as separate output objects.
"""

import pulsar
from pulsar.schema import JsonSchema
from langchain_community.document_loaders import PyPDFLoader
import tempfile
import base64
import os
import argparse
import rdflib
import json
import urllib.parse
import time

from ... schema import VectorsChunk, Triple, Source, Value
from ... log_level import LogLevel
from ... llm_client import LlmClient
from ... prompts import to_definitions
from ... rdf import TRUSTGRAPH_ENTITIES, DEFINITION

DEFINITION_VALUE = Value(value=DEFINITION, is_uri=True)

class Processor:

    def __init__(
            self,
            pulsar_host,
            input_queue,
            output_queue,
            subscriber,
            log_level,
    ):

        self.client = pulsar.Client(
            pulsar_host,
            logger=pulsar.ConsoleLogger(log_level.to_pulsar())
        )

        self.consumer = self.client.subscribe(
            input_queue, subscriber,
            schema=JsonSchema(VectorsChunk),
        )

        self.producer = self.client.create_producer(
            topic=output_queue,
            schema=JsonSchema(Triple),
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

    def run(self):

        while True:

            msg = self.consumer.receive()

            try:

                v = msg.value()
                print(f"Indexing {v.source.id}...", flush=True)

                chunk = v.chunk.decode("utf-8")

                g = rdflib.Graph()

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

                # Acknowledge successful processing of the message
                self.consumer.acknowledge(msg)

            except Exception as e:

                print("Exception: ", e, flush=True)

                # Message failed to be processed
                self.consumer.negative_acknowledge(msg)

    def __del__(self):
        self.client.close()

def run():

    parser = argparse.ArgumentParser(
        prog='pdf-decoder',
        description=__doc__,
    )

    default_pulsar_host = os.getenv("PULSAR_HOST", 'pulsar://pulsar:6650')
    default_input_queue = 'vectors-chunk-load'
    default_output_queue = 'graph-load'
    default_subscriber = 'kg-extract-definitions'

    parser.add_argument(
        '-p', '--pulsar-host',
        default=default_pulsar_host,
        help=f'Pulsar host (default: {default_pulsar_host})',
    )

    parser.add_argument(
        '-i', '--input-queue',
        default=default_input_queue,
        help=f'Input queue (default: {default_input_queue})'
    )

    parser.add_argument(
        '-s', '--subscriber',
        default=default_subscriber,
        help=f'Queue subscriber name (default: {default_subscriber})'
    )

    parser.add_argument(
        '-o', '--output-queue',
        default=default_output_queue,
        help=f'Output queue (default: {default_output_queue})'
    )

    parser.add_argument(
        '-l', '--log-level',
        type=LogLevel,
        default=LogLevel.INFO,
        choices=list(LogLevel),
        help=f'Output queue (default: info)'
    )

    args = parser.parse_args()

    while True:

        try:

            p = Processor(
                pulsar_host=args.pulsar_host,
                input_queue=args.input_queue,
                output_queue=args.output_queue,
                subscriber=args.subscriber,
                log_level=args.log_level,
            )

            p.run()

        except Exception as e:

            print("Exception:", e, flush=True)
            print("Will retry...", flush=True)

        time.sleep(10)

