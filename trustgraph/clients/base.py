
import pulsar
import _pulsar
import hashlib
import uuid
import time
from pulsar.schema import JsonSchema

from .. exceptions import *

# Ugly
ERROR=_pulsar.LoggerLevel.Error
WARN=_pulsar.LoggerLevel.Warn
INFO=_pulsar.LoggerLevel.Info
DEBUG=_pulsar.LoggerLevel.Debug

class BaseClient:

    def __init__(
            self, log_level=ERROR,
            subscriber=None,
            input_queue=None,
            output_queue=None,
            input_schema=None,
            output_schema=None,
            pulsar_host="pulsar://pulsar:6650",
    ):

        if input_queue == None: raise RuntimeError("Need input_queue")
        if output_queue == None: raise RuntimeError("Need output_queue")
        if input_schema == None: raise RuntimeError("Need input_schema")
        if output_schema == None: raise RuntimeError("Need output_schema")

        if subscriber == None:
            subscriber = str(uuid.uuid4())

        self.client = pulsar.Client(
            pulsar_host,
            logger=pulsar.ConsoleLogger(log_level),
        )

        self.producer = self.client.create_producer(
            topic=input_queue,
            schema=JsonSchema(input_schema),
            chunking_enabled=True,
        )

        self.consumer = self.client.subscribe(
            output_queue, subscriber,
            schema=JsonSchema(output_schema),
        )

        self.input_schema = input_schema
        self.output_schema = output_schema

    def call(self, **args):

        timeout = args.get("timeout", 30)

        if "timeout" in args:
            del args["timeout"]

        id = str(uuid.uuid4())

        r = self.input_schema(**args)

        end_time = time.time() + timeout

        self.producer.send(r, properties={ "id": id })

        while time.time() < end_time:

            try:
                msg = self.consumer.receive(timeout_millis=5000)
            except pulsar.exceptions.Timeout:
                continue

            mid = msg.properties()["id"]

            if mid == id:

                value = msg.value()

                if value.error:

                    self.consumer.acknowledge(msg)

                    if value.error.type == "llm-error":
                        raise LlmError(value.error.message)

                    elif value.error.type == "too-many-requests":
                        raise TooManyRequests(value.error.message)

                    elif value.error.type == "ParseError":
                        raise ParseError(value.error.message)

                    else:

                        raise RuntimeError(
                            f"{value.error.type}: {value.error.message}"
                        )

                resp = msg.value()
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

