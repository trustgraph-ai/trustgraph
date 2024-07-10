
"""
Simple RAG service, performs query using graph RAG an LLM.
Input is query, output is response.
"""

import pulsar
from pulsar.schema import JsonSchema
import tempfile
import base64
import os
import argparse
import time

from ... schema import GraphRagQuery, GraphRagResponse
from ... log_level import LogLevel
from ... graph_rag import GraphRag

class Processor:

    def __init__(
            self,
            pulsar_host,
            input_queue,
            output_queue,
            subscriber,
            log_level,
            graph_hosts,
            vector_store,
    ):

        self.client = pulsar.Client(
            pulsar_host,
            logger=pulsar.ConsoleLogger(log_level.to_pulsar())
        )

        self.consumer = self.client.subscribe(
            input_queue, subscriber,
            schema=JsonSchema(GraphRagQuery),
        )

        self.producer = self.client.create_producer(
            topic=output_queue,
            schema=JsonSchema(GraphRagResponse),
        )

        self.rag = GraphRag(
            pulsar_host=pulsar_host,
            graph_hosts=graph_hosts,
            vector_store=vector_store,
            verbose=True,
        )

    def run(self):

        while True:

            msg = self.consumer.receive()

            try:

                v = msg.value()

	        # Sender-produced ID

                id = msg.properties()["id"]

                print(f"Handling input {id}...", flush=True)

                response = self.rag.query(v.query)

                print("Send response...", flush=True)
                r = GraphRagResponse(response = response)
                self.producer.send(r, properties={"id": id})

                print("Done.", flush=True)

                # Acknowledge successful processing of the message
                self.consumer.acknowledge(msg)

            except Exception as e:

                print("Exception:", e, flush=True)

                # Message failed to be processed
                self.consumer.negative_acknowledge(msg)

    def __del__(self):
        print("Closing", flush=True)
        self.client.close()

def run():

    parser = argparse.ArgumentParser(
        prog='llm-ollama-text',
        description=__doc__,
    )

    default_pulsar_host = os.getenv("PULSAR_HOST", 'pulsar://pulsar:6650')
    default_input_queue = 'graph-rag-query'
    default_output_queue = 'graph-rag-response'
    default_subscriber = 'graph-rag'

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
        '-g', '--graph-hosts',
        default='cassandra',
        help=f'Graph hosts, comma separated (default: cassandra)'
    )

    parser.add_argument(
        '-v', '--vector-store',
        default='http://milvus:19530',
        help=f'Vector host (default: http://milvus:19530)'
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
                graph_hosts=args.graph_hosts.split(","),
                vector_store=args.vector_store,
            )

            p.run()

        except Exception as e:

            print("Exception:", e, flush=True)
            print("Will retry...", flush=True)

        time.sleep(10)

