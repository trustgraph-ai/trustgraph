
import pulsar
import _pulsar
import hashlib
import uuid
import time
from pulsar.schema import JsonSchema

from .. exceptions import *
from ..base.pubsub import get_pubsub

# Default timeout for a request/response.  In seconds.
DEFAULT_TIMEOUT=300

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
            pulsar_api_key=None,
            listener=None,
    ):

        if input_queue == None: raise RuntimeError("Need input_queue")
        if output_queue == None: raise RuntimeError("Need output_queue")
        if input_schema == None: raise RuntimeError("Need input_schema")
        if output_schema == None: raise RuntimeError("Need output_schema")

        if subscriber == None:
            subscriber = str(uuid.uuid4())

        # Create backend using factory
        self.backend = get_pubsub(
            pulsar_host=pulsar_host,
            pulsar_api_key=pulsar_api_key,
            pulsar_listener=listener,
            pubsub_backend='pulsar'
        )

        self.producer = self.backend.create_producer(
            topic=input_queue,
            schema=input_schema,
            chunking_enabled=True,
        )

        self.consumer = self.backend.create_consumer(
            topic=output_queue,
            subscription=subscriber,
            schema=output_schema,
            consumer_type='shared',
        )

        self.input_schema = input_schema
        self.output_schema = output_schema

    def call(self, **args):

        timeout = args.get("timeout", DEFAULT_TIMEOUT)
        inspect = args.get("inspect", lambda x: True)

        if "timeout" in args:
            del args["timeout"]

        if "inspect" in args:
            del args["inspect"]

        id = str(uuid.uuid4())

        r = self.input_schema(**args)

        end_time = time.time() + timeout

        self.producer.send(r, properties={ "id": id })

        while time.time() < end_time:

            try:
                msg = self.consumer.receive(timeout_millis=2500)
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

                complete = inspect(value)

                if not complete: continue

                resp = msg.value()
                self.consumer.acknowledge(msg)
                return resp

            # Ignore messages with wrong ID
            self.consumer.acknowledge(msg)

        raise TimeoutError("Timed out waiting for response")

    def __del__(self):

        if hasattr(self, "consumer"):
            self.consumer.close()

        if hasattr(self, "producer"):
            self.producer.flush()
            self.producer.close()

        if hasattr(self, "backend"):
            self.backend.close()

