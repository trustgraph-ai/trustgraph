#!/usr/bin/env python3

import pulsar
import _pulsar
from pulsar.schema import JsonSchema
from trustgraph.schema import TextCompletionRequest, TextCompletionResponse
import hashlib
import uuid

# Ugly
ERROR=_pulsar.LoggerLevel.Error
WARN=_pulsar.LoggerLevel.Warn
INFO=_pulsar.LoggerLevel.Info
DEBUG=_pulsar.LoggerLevel.Debug

class LlmClient:

    def __init__(
            self, log_level=ERROR, client_id=None,
            pulsar_host="pulsar://pulsar:6650",
    ):

        if client_id == None:
            client_id = str(uuid.uuid4())

        self.client = pulsar.Client(
            pulsar_host,
            logger=pulsar.ConsoleLogger(log_level),
        )

        self.producer = self.client.create_producer(
            topic='llm-complete-text',
            schema=JsonSchema(TextCompletionRequest),
            chunking_enabled=True,
        )

        self.consumer = self.client.subscribe(
            'llm-complete-text-response', client_id,
            schema=JsonSchema(TextCompletionResponse),
        )

    def request(self, prompt, timeout=500):

        id = str(uuid.uuid4())

        r = TextCompletionRequest(
            prompt=prompt
        )

        self.producer.send(r, properties={ "id": id })

        while True:

            msg = self.consumer.receive(timeout_millis=timeout * 1000)

            mid = msg.properties()["id"]

            if mid == id:
                resp = msg.value().response
                self.consumer.acknowledge(msg)
                return resp

            # Ignore messages with wrong ID
            self.consumer.acknowledge(msg)

    def __del__(self):

        self.producer.close()
        self.consumer.close()
        self.client.close()

