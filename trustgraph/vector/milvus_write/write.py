
"""
Accepts entity/vector pairs and writes them to a Milvus store.
"""

import pulsar
from pulsar.schema import JsonSchema
from langchain_community.document_loaders import PyPDFLoader
import tempfile
import base64
import os
import argparse
import time

from ... schema import VectorsAssociation
from ... log_level import LogLevel
from ... triple_vectors import TripleVectors

default_pulsar_host = os.getenv("PULSAR_HOST", 'pulsar://pulsar:6650')
default_input_queue = 'vectors-load'
default_subscriber = 'vector-write-milvus'
default_store_uri = 'http://localhost:19530'

class Processor:

    def __init__(
            self,
            pulsar_host=default_pulsar_host,
            input_queue=default_input_queue,
            subscriber=default_subscriber,
            store_uri=default_store_uri,
            log_level=LogLevel.INFO,
    ):

        self.client = None

        self.client = pulsar.Client(
            pulsar_host,
            logger=pulsar.ConsoleLogger(log_level.to_pulsar())
        )

        self.consumer = self.client.subscribe(
            input_queue, subscriber,
            schema=JsonSchema(VectorsAssociation),
        )

        self.vecstore = TripleVectors(store_uri)

    def run(self):

        while True:

            msg = self.consumer.receive()

            try:

                v = msg.value()

                if v.entity.value != "":
                    for vec in v.vectors:
                        self.vecstore.insert(vec, v.entity.value)

                # Acknowledge successful processing of the message
                self.consumer.acknowledge(msg)

            except Exception as e:

                print("Exception:", e, flush=True)

                # Message failed to be processed
                self.consumer.negative_acknowledge(msg)

    def __del__(self):

        if self.client:
            self.client.close()

def run():

    parser = argparse.ArgumentParser(
        prog='pdf-decoder',
        description=__doc__,
    )

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
        '-l', '--log-level',
        type=LogLevel,
        default=LogLevel.INFO,
        choices=list(LogLevel),
        help=f'Output queue (default: info)'
    )

    parser.add_argument(
        '-t', '--store-uri',
        default="http://milvus:19530",
        help=f'Milvus store URI (default: http://milvus:19530)'
    )

    args = parser.parse_args()

    while True:

        try:

            p = Processor(
                pulsar_host=args.pulsar_host,
                input_queue=args.input_queue,
                subscriber=args.subscriber,
                store_uri=args.store_uri,
                log_level=args.log_level,
            )

            p.run()

        except Exception as e:

            print("Exception:", e, flush=True)
            print("Will retry...", flush=True)

        time.sleep(10)


