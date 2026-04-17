"""
Unit tests for RabbitMQ backend — topic parsing and factory dispatch.
Does not require a running RabbitMQ instance.
"""

import pytest
import argparse

pika = pytest.importorskip("pika", reason="pika not installed")

from trustgraph.base.rabbitmq_backend import RabbitMQBackend
from trustgraph.base.pubsub import get_pubsub, add_pubsub_args


class TestRabbitMQParseTopic:

    @pytest.fixture
    def backend(self):
        b = object.__new__(RabbitMQBackend)
        return b

    def test_flow_is_durable(self, backend):
        exchange, cls, durable = backend._parse_topic('flow:tg:text-completion-request')
        assert durable is True
        assert cls == 'flow'
        assert exchange == 'tg.flow.text-completion-request'

    def test_notify_is_not_durable(self, backend):
        exchange, cls, durable = backend._parse_topic('notify:tg:config')
        assert durable is False
        assert cls == 'notify'
        assert exchange == 'tg.notify.config'

    def test_request_is_not_durable(self, backend):
        exchange, cls, durable = backend._parse_topic('request:tg:config')
        assert durable is False
        assert cls == 'request'
        assert exchange == 'tg.request.config'

    def test_response_is_not_durable(self, backend):
        exchange, cls, durable = backend._parse_topic('response:tg:librarian')
        assert durable is False
        assert cls == 'response'
        assert exchange == 'tg.response.librarian'

    def test_custom_topicspace(self, backend):
        exchange, cls, durable = backend._parse_topic('flow:prod:my-queue')
        assert exchange == 'prod.flow.my-queue'
        assert durable is True

    def test_no_colon_defaults_to_flow(self, backend):
        exchange, cls, durable = backend._parse_topic('simple-queue')
        assert exchange == 'tg.flow.simple-queue'
        assert cls == 'flow'
        assert durable is True

    def test_invalid_class_raises(self, backend):
        with pytest.raises(ValueError, match="Invalid topic class"):
            backend._parse_topic('unknown:tg:topic')

    def test_topic_with_flow_suffix(self, backend):
        """Topic names with flow suffix (e.g. :default) are preserved."""
        exchange, cls, durable = backend._parse_topic('request:tg:prompt:default')
        assert exchange == 'tg.request.prompt:default'


class TestGetPubsubRabbitMQ:

    def test_factory_creates_rabbitmq_backend(self):
        backend = get_pubsub(pubsub_backend='rabbitmq')
        assert isinstance(backend, RabbitMQBackend)

    def test_factory_passes_config(self):
        backend = get_pubsub(
            pubsub_backend='rabbitmq',
            rabbitmq_host='myhost',
            rabbitmq_port=5673,
            rabbitmq_username='user',
            rabbitmq_password='pass',
            rabbitmq_vhost='/test',
        )
        assert isinstance(backend, RabbitMQBackend)
        # Verify connection params were set
        params = backend._connection_params
        assert params.host == 'myhost'
        assert params.port == 5673
        assert params.virtual_host == '/test'


class TestAddPubsubArgsRabbitMQ:

    def test_rabbitmq_args_present(self):
        parser = argparse.ArgumentParser()
        add_pubsub_args(parser)
        args = parser.parse_args([
            '--pubsub-backend', 'rabbitmq',
            '--rabbitmq-host', 'myhost',
            '--rabbitmq-port', '5673',
        ])
        assert args.pubsub_backend == 'rabbitmq'
        assert args.rabbitmq_host == 'myhost'
        assert args.rabbitmq_port == 5673

    def test_rabbitmq_defaults_container(self):
        parser = argparse.ArgumentParser()
        add_pubsub_args(parser)
        args = parser.parse_args([])
        assert args.rabbitmq_host == 'rabbitmq'
        assert args.rabbitmq_port == 5672
        assert args.rabbitmq_username == 'guest'
        assert args.rabbitmq_password == 'guest'
        assert args.rabbitmq_vhost == '/'
