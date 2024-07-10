
"""
Vectorizer, applies an embedding algorithm to a chunk.  Input is a chunk,
output is chunk and vectors.
"""

import pulsar
from pulsar.schema import JsonSchema
import tempfile
import base64
import os
import argparse
import time

from ... schema import Chunk, VectorsChunk
from ... embeddings_client import EmbeddingsClient
from ... log_level import LogLevel

class Processor:

    def __init__(
            self,
            pulsar_host,
            input_queue,
            output_queue,
            subscriber,
            log_level,
            model,
    ):

        self.client = pulsar.Client(
            pulsar_host,
            logger=pulsar.ConsoleLogger(log_level.to_pulsar())
        )

        self.consumer = self.client.subscribe(
            input_queue, subscriber,
            schema=JsonSchema(Chunk),
        )

        self.producer = self.client.create_producer(
            topic=output_queue,
            schema=JsonSchema(VectorsChunk),
        )

        self.embeddings = EmbeddingsClient(pulsar_host=pulsar_host)

    def emit(self, source, chunk, vectors):

        r = VectorsChunk(source=source, chunk=chunk, vectors=vectors)
        self.producer.send(r)

    def run(self):

        while True:

            msg = self.consumer.receive()

            try:

                v = msg.value()
                print(f"Indexing {v.source.id}...", flush=True)

                chunk = v.chunk.decode("utf-8")

                try:

                    vectors = self.embeddings.request(chunk)

                    self.emit(
                        source=v.source,
                        chunk=chunk.encode("utf-8"),
                        vectors=vectors
                    )

                except Exception as e:
                    print("Exception:", e, flush=True)

                print("Done.", flush=True)

                # Acknowledge successful processing of the message
                self.consumer.acknowledge(msg)

            except Exception as e:

                print("Exception:", e, flush=True)

                # Message failed to be processed
                self.consumer.negative_acknowledge(msg)

    def __del__(self):
        self.client.close()

def run():

    parser = argparse.ArgumentParser(
        prog='embeddings-vectorizer',
        description=__doc__,
    )

    default_pulsar_host = os.getenv("PULSAR_HOST", 'pulsar://pulsar:6650')
    default_input_queue = 'chunk-load'
    default_output_queue = 'vectors-chunk-load'
    default_subscriber = 'embeddings-vectorizer'

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

    parser.add_argument(
        '-m', '--model',
        default="all-MiniLM-L6-v2",
        help=f'LLM model (default: all-MiniLM-L6-v2)'
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
                model=args.model,
            )

            p.run()

        except Exception as e:

            print("Exception:", e, flush=True)
            print("Will retry...", flush=True)

        time.sleep(10)

