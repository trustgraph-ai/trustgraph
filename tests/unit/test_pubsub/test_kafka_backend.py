"""
Unit tests for Kafka backend — topic parsing and factory dispatch.
Does not require a running Kafka instance.
"""

import pytest
import argparse

from trustgraph.base.kafka_backend import KafkaBackend
from trustgraph.base.pubsub import get_pubsub, add_pubsub_args


class TestKafkaParseTopic:

    @pytest.fixture
    def backend(self):
        b = object.__new__(KafkaBackend)
        return b

    def test_flow_is_durable(self, backend):
        name, cls, durable = backend._parse_topic('flow:tg:text-completion-request')
        assert durable is True
        assert cls == 'flow'
        assert name == 'tg.flow.text-completion-request'

    def test_notify_is_not_durable(self, backend):
        name, cls, durable = backend._parse_topic('notify:tg:config')
        assert durable is False
        assert cls == 'notify'
        assert name == 'tg.notify.config'

    def test_request_is_not_durable(self, backend):
        name, cls, durable = backend._parse_topic('request:tg:config')
        assert durable is False
        assert cls == 'request'
        assert name == 'tg.request.config'

    def test_response_is_not_durable(self, backend):
        name, cls, durable = backend._parse_topic('response:tg:librarian')
        assert durable is False
        assert cls == 'response'
        assert name == 'tg.response.librarian'

    def test_custom_topicspace(self, backend):
        name, cls, durable = backend._parse_topic('flow:prod:my-queue')
        assert name == 'prod.flow.my-queue'
        assert durable is True

    def test_no_colon_defaults_to_flow(self, backend):
        name, cls, durable = backend._parse_topic('simple-queue')
        assert name == 'tg.flow.simple-queue'
        assert cls == 'flow'
        assert durable is True

    def test_invalid_class_raises(self, backend):
        with pytest.raises(ValueError, match="Invalid topic class"):
            backend._parse_topic('unknown:tg:topic')

    def test_topic_with_flow_suffix(self, backend):
        """Topic names with flow suffix (e.g. :default) have colons replaced with dots."""
        name, cls, durable = backend._parse_topic('request:tg:prompt:default')
        assert name == 'tg.request.prompt.default'


class TestKafkaRetention:

    @pytest.fixture
    def backend(self):
        b = object.__new__(KafkaBackend)
        return b

    def test_flow_gets_long_retention(self, backend):
        assert backend._retention_ms('flow') == 7 * 24 * 60 * 60 * 1000

    def test_request_gets_short_retention(self, backend):
        assert backend._retention_ms('request') == 300 * 1000

    def test_response_gets_short_retention(self, backend):
        assert backend._retention_ms('response') == 300 * 1000

    def test_notify_gets_short_retention(self, backend):
        assert backend._retention_ms('notify') == 300 * 1000


class TestGetPubsubKafka:

    def test_factory_creates_kafka_backend(self):
        backend = get_pubsub(pubsub_backend='kafka')
        assert isinstance(backend, KafkaBackend)

    def test_factory_passes_config(self):
        backend = get_pubsub(
            pubsub_backend='kafka',
            kafka_bootstrap_servers='myhost:9093',
            kafka_security_protocol='SASL_SSL',
            kafka_sasl_mechanism='PLAIN',
            kafka_sasl_username='user',
            kafka_sasl_password='pass',
        )
        assert isinstance(backend, KafkaBackend)
        assert backend._bootstrap_servers == 'myhost:9093'
        assert backend._admin_config['security.protocol'] == 'SASL_SSL'
        assert backend._admin_config['sasl.mechanism'] == 'PLAIN'
        assert backend._admin_config['sasl.username'] == 'user'
        assert backend._admin_config['sasl.password'] == 'pass'


class TestAddPubsubArgsKafka:

    def test_kafka_args_present(self):
        parser = argparse.ArgumentParser()
        add_pubsub_args(parser)
        args = parser.parse_args([
            '--pubsub-backend', 'kafka',
            '--kafka-bootstrap-servers', 'myhost:9093',
        ])
        assert args.pubsub_backend == 'kafka'
        assert args.kafka_bootstrap_servers == 'myhost:9093'

    def test_kafka_defaults_container(self):
        parser = argparse.ArgumentParser()
        add_pubsub_args(parser)
        args = parser.parse_args([])
        assert args.kafka_bootstrap_servers == 'kafka:9092'
        assert args.kafka_security_protocol == 'PLAINTEXT'

    def test_kafka_standalone_defaults_to_localhost(self):
        parser = argparse.ArgumentParser()
        add_pubsub_args(parser, standalone=True)
        args = parser.parse_args([])
        assert args.kafka_bootstrap_servers == 'localhost:9092'
