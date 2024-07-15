
"""
Simple decoder, accepts text documents on input, outputs chunks from the
as text as separate output objects.
"""

import pulsar
from pulsar.schema import JsonSchema
import tempfile
import base64
import os
import argparse
from langchain_text_splitters import RecursiveCharacterTextSplitter
import time

from ... schema import TextDocument, Chunk, Source
from ... log_level import LogLevel

default_pulsar_host = os.getenv("PULSAR_HOST", 'pulsar://pulsar:6650')
default_input_queue = 'text-doc-load'
default_output_queue = 'chunk-load'
default_subscriber = 'chunker-recursive'

class Processor:

    def __init__(
            self,
            pulsar_host=default_pulsar_host,
            input_queue=default_input_queue,
            output_queue=default_output_queue,
            subscriber=default_subscriber,
            log_level=LogLevel.INFO,
    ):

        self.client = None
        
        self.client = pulsar.Client(
            pulsar_host,
            logger=pulsar.ConsoleLogger(log_level.to_pulsar())
        )

        self.consumer = self.client.subscribe(
            input_queue, subscriber,
            schema=JsonSchema(TextDocument),
        )

        self.producer = self.client.create_producer(
            topic=output_queue,
            schema=JsonSchema(Chunk),
        )

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=20,
            length_function=len,
            is_separator_regex=False,
        )

        print("Chunker inited")

    def run(self):

        print("Chunker running")

        while True:

            msg = self.consumer.receive()
            print("Chunker message received")

            try:

                v = msg.value()
                print(f"Chunking {v.source.id}...", flush=True)

                texts = self.text_splitter.create_documents(
                    [v.text.decode("utf-8")]
                )

                for ix, chunk in enumerate(texts):

                    id = v.source.id + "-c" + str(ix)

                    r = Chunk(
                        source=Source(
                            source=v.source.source,
                            id=id,
                            title=v.source.title
                        ),
                        chunk=chunk.page_content.encode("utf-8"),
                    )

                    self.producer.send(r)

                # Acknowledge successful processing of the message
                self.consumer.acknowledge(msg)

                print("Done.", flush=True)

            except Exception as e:
                print(e, flush=True)

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


