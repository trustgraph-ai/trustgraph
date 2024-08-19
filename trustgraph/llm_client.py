#!/usr/bin/env python3

import pulsar
import _pulsar
from pulsar.schema import JsonSchema
import hashlib
import uuid

from . schema import TextCompletionRequest, TextCompletionResponse
from . schema import text_completion_request_queue
from . schema import text_completion_response_queue

# Ugly
ERROR=_pulsar.LoggerLevel.Error
WARN=_pulsar.LoggerLevel.Warn
INFO=_pulsar.LoggerLevel.Info
DEBUG=_pulsar.LoggerLevel.Debug

class LlmClient:

    def __init__(
            self, log_level=ERROR,
            subscriber=None,
            input_queue=None,
            output_queue=None,
            pulsar_host="pulsar://pulsar:6650",
    ):

        if input_queue == None:
            input_queue = text_completion_request_queue

        if output_queue == None:
            output_queue = text_completion_response_queue

        if subscriber == None:
            subscriber = str(uuid.uuid4())

        self.client = pulsar.Client(
            pulsar_host,
            logger=pulsar.ConsoleLogger(log_level),
        )

        self.producer = self.client.create_producer(
            topic=input_queue,
            schema=JsonSchema(TextCompletionRequest),
            chunking_enabled=True,
        )

        self.consumer = self.client.subscribe(
            output_queue, subscriber,
            schema=JsonSchema(TextCompletionResponse),
        )

    def request(self, prompt, timeout=30):

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

        if hasattr(self, "consumer"):
#             self.consumer.unsubscribe()
            self.consumer.close()
            
        if hasattr(self, "producer"):
            self.producer.flush()
            self.producer.close()
            
        self.client.close()

