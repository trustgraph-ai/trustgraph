
import pulsar
import _pulsar
from pulsar.schema import JsonSchema
from .. schema import GraphRagQuery, GraphRagResponse
from .. schema import graph_rag_request_queue, graph_rag_response_queue

import hashlib
import uuid
import time

# Ugly
ERROR=_pulsar.LoggerLevel.Error
WARN=_pulsar.LoggerLevel.Warn
INFO=_pulsar.LoggerLevel.Info
DEBUG=_pulsar.LoggerLevel.Debug

class GraphRagClient:

    def __init__(
            self, log_level=ERROR, subscriber=None,
            pulsar_host="pulsar://pulsar:6650",
    ):

        if subscriber == None:
            subscriber = str(uuid.uuid4())

        self.client = pulsar.Client(
            pulsar_host,
            logger=pulsar.ConsoleLogger(log_level),
        )

        self.producer = self.client.create_producer(
            topic=graph_rag_request_queue,
            schema=JsonSchema(GraphRagQuery),
            chunking_enabled=True,
        )

        self.consumer = self.client.subscribe(
            graph_rag_response_queue, subscriber,
            schema=JsonSchema(GraphRagResponse),
        )

    def request(self, query, timeout=500):

        id = str(uuid.uuid4())

        r = GraphRagQuery(
            query=query
        )
        self.producer.send(r, properties={ "id": id })

        end_time = time.time() + timeout

        while time.time() < end_time:

            try:
                msg = self.consumer.receive(timeout_millis=5000)
            except pulsar.exceptions.Timeout:
                continue

            mid = msg.properties()["id"]

            if mid == id:
                resp = msg.value().response
                self.consumer.acknowledge(msg)
                return resp

            # Ignore messages with wrong ID
            self.consumer.acknowledge(msg)

        raise TimeoutError("Timed out waiting for response")

    def __del__(self):

        if hasattr(self, "consumer"):
#             self.consumer.unsubscribe()
            self.consumer.close()
            
        if hasattr(self, "producer"):
            self.producer.flush()
            self.producer.close()
            
        self.client.close()

