
"""
Simple decoder, accepts PDF documents on input, outputs pages from the
PDF document as text as separate output objects.
"""

import pulsar
from pulsar.schema import JsonSchema
import tempfile
import base64
import os
import argparse
import time

from ... trustgraph import TrustGraph
from ... schema import Triple
from ... log_level import LogLevel

class Processor:

    def __init__(
            self,
            pulsar_host,
            input_queue,
            subscriber,
            log_level,
            graph_host,
    ):

        self.client = pulsar.Client(
            pulsar_host,
            logger=pulsar.ConsoleLogger(log_level.to_pulsar())
        )

        self.consumer = self.client.subscribe(
            input_queue, subscriber,
            schema=JsonSchema(Triple),
        )

        self.tg = TrustGraph([graph_host])

        self.count = 0

    def run(self):

        while True:

            msg = self.consumer.receive()

            try:

                v = msg.value()

                self.tg.insert(
                    v.s.value,
                    v.p.value,
                    v.o.value
                )

                self.count += 1

                if (self.count % 1000) == 0:
                    print(self.count, "...", flush=True)

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
        prog='graph-write-cassandra',
        description=__doc__,
    )

    default_pulsar_host = os.getenv("PULSAR_HOST", 'pulsar://pulsar:6650')
    default_input_queue = 'graph-load'
    default_subscriber = 'graph-write-cassandra'

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
        '-g', '--graph-host',
        default="localhost",
        help=f'Output queue (default: localhost)'
    )

    args = parser.parse_args()

    while True:

        try:

            p = Processor(
                pulsar_host=args.pulsar_host,
                input_queue=args.input_queue,
                subscriber=args.subscriber,
                log_level=args.log_level,
                graph_host=args.graph_host,
            )

            p.run()

        except Exception as e:

            print("Exception:", e, flush=True)
            print("Will retry...", flush=True)

        time.sleep(10)


