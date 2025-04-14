
import os
import pulsar
import uuid
from pulsar.schema import JsonSchema

from .. log_level import LogLevel

class PulsarClient:

    default_pulsar_host = os.getenv("PULSAR_HOST", 'pulsar://pulsar:6650')
    default_pulsar_api_key = os.getenv("PULSAR_API_KEY", None)

    def __init__(self, **params):

        self.client = None

        pulsar_host = params.get("pulsar_host", self.default_pulsar_host)
        pulsar_listener = params.get("pulsar_listener", None)
        pulsar_api_key = params.get(
            "pulsar_api_key",
            self.default_pulsar_api_key
        )
        log_level = params.get("log_level", LogLevel.INFO)

        self.pulsar_host = pulsar_host
        self.pulsar_api_key = pulsar_api_key

        if pulsar_api_key:
            auth = pulsar.AuthenticationToken(pulsar_api_key)
            self.client = pulsar.Client(
                pulsar_host,
                authentication=auth,
                logger=pulsar.ConsoleLogger(log_level.to_pulsar())
            )
        else:
            self.client = pulsar.Client(
                pulsar_host,
                listener_name=pulsar_listener,
                logger=pulsar.ConsoleLogger(log_level.to_pulsar())
            )

        self.pulsar_listener = pulsar_listener

    def close(self):
        self.client.close()

    def __del__(self):

        if hasattr(self, "client"):
            if self.client:
                self.client.close()

    def subscribe(self, queue, subscriber, schema):

        return self.client.subscribe(
            queue, subscriber,
            consumer_type=pulsar.ConsumerType.Shared,
            schema=JsonSchema(schema),
        )

    def publish(self, queue, schema):

        return self.client.create_producer(
            topic=queue,
            schema=JsonSchema(schema),
            chunking_enabled=True,
        )

    @staticmethod
    def add_args(parser):

        parser.add_argument(
            '-p', '--pulsar-host',
            default=__class__.default_pulsar_host,
            help=f'Pulsar host (default: {__class__.default_pulsar_host})',
        )
        
        parser.add_argument(
            '--pulsar-api-key',
            default=__class__.default_pulsar_api_key,
            help=f'Pulsar API key',
        )

        parser.add_argument(
            '--pulsar-listener',
            help=f'Pulsar listener (default: none)',
        )

        parser.add_argument(
            '-l', '--log-level',
            type=LogLevel,
            default=LogLevel.INFO,
            choices=list(LogLevel),
            help=f'Output queue (default: info)'
        )
