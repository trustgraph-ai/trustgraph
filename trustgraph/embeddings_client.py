#!/usr/bin/env python3

import pulsar
import _pulsar
from pulsar.schema import JsonSchema
from . schema import EmbeddingsRequest, EmbeddingsResponse
from . schema import embeddings_request_queue, embeddings_response_queue
import hashlib
import uuid

# Ugly
ERROR=_pulsar.LoggerLevel.Error
WARN=_pulsar.LoggerLevel.Warn
INFO=_pulsar.LoggerLevel.Info
DEBUG=_pulsar.LoggerLevel.Debug

class EmbeddingsClient:

    def __init__(
            self, log_level=ERROR, client_id=None,
            pulsar_host="pulsar://pulsar:6650",
    ):

        self.client = None

        if client_id == None:
            client_id = str(uuid.uuid4())

        self.client = pulsar.Client(
            pulsar_host,
            logger=pulsar.ConsoleLogger(log_level),
        )

        self.producer = self.client.create_producer(
            topic=embeddings_request_queue,
            schema=JsonSchema(EmbeddingsRequest),
            chunking_enabled=True,
        )

        self.consumer = self.client.subscribe(
            embeddings_response_queue, client_id,
            schema=JsonSchema(EmbeddingsResponse),
        )

    def request(self, text, timeout=500):

        id = str(uuid.uuid4())

        r = EmbeddingsRequest(
            text=text
        )
        self.producer.send(r, properties={ "id": id })

        while True:

            msg = self.consumer.receive(timeout_millis=timeout * 1000)

            mid = msg.properties()["id"]

            if mid == id:
                resp = msg.value().vectors
                self.consumer.acknowledge(msg)
                return resp

            # Ignore messages with wrong ID
            self.consumer.acknowledge(msg)

    def __del__(self):

        if self.client:
            self.client.close()

