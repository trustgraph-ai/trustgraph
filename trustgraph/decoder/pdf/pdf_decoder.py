
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
import time

from ... schema import Document, TextDocument, Source
from ... log_level import LogLevel

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
            schema=JsonSchema(Document),
        )

        self.producer = self.client.create_producer(
            topic=output_queue,
            schema=JsonSchema(TextDocument),
        )

    def run(self):

        while True:

            msg = self.consumer.receive()

            try:

                v = msg.value()
                print(f"Decoding {v.source.id}...", flush=True)

                with tempfile.NamedTemporaryFile(delete_on_close=False) as fp:

                    fp.write(base64.b64decode(v.data))
                    fp.close()

                    with open(fp.name, mode='rb') as f:

                        loader = PyPDFLoader(fp.name)
                        pages = loader.load()

                        for ix, page in enumerate(pages):

                            id = v.source.id + "-p" + str(ix)
                            r = TextDocument(
                                source=Source(
                                    source=v.source.source,
                                    title=v.source.title,
                                    id=id,
                                ),
                                text=page.page_content.encode("utf-8"),
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
        self.client.close()

def run():

    parser = argparse.ArgumentParser(
        prog='pdf-decoder',
        description=__doc__,
    )

    default_pulsar_host = os.getenv("PULSAR_HOST", 'pulsar://pulsar:6650')
    default_input_queue = 'document-load'
    default_output_queue = 'text-doc-load'
    default_subscriber = 'pdf-decoder'

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

