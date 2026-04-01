"""
Tests for queue naming and topic mapping.
"""

import pytest
import argparse

from trustgraph.schema.core.topic import queue
from trustgraph.base.pubsub import get_pubsub, add_pubsub_args
from trustgraph.base.pulsar_backend import PulsarBackend


class TestQueueFunction:

    def test_flow_default(self):
        assert queue('text-completion-request') == 'flow:tg:text-completion-request'

    def test_request_class(self):
        assert queue('config', cls='request') == 'request:tg:config'

    def test_response_class(self):
        assert queue('config', cls='response') == 'response:tg:config'

    def test_state_class(self):
        assert queue('config', cls='state') == 'state:tg:config'

    def test_custom_topicspace(self):
        assert queue('config', cls='request', topicspace='prod') == 'request:prod:config'

    def test_default_class_is_flow(self):
        result = queue('something')
        assert result.startswith('flow:')


class TestPulsarMapTopic:

    @pytest.fixture
    def backend(self):
        """Create a PulsarBackend without connecting."""
        b = object.__new__(PulsarBackend)
        return b

    def test_flow_maps_to_persistent(self, backend):
        assert backend.map_topic('flow:tg:text-completion-request') == \
            'persistent://tg/flow/text-completion-request'

    def test_state_maps_to_persistent(self, backend):
        assert backend.map_topic('state:tg:config') == \
            'persistent://tg/state/config'

    def test_request_maps_to_non_persistent(self, backend):
        assert backend.map_topic('request:tg:config') == \
            'non-persistent://tg/request/config'

    def test_response_maps_to_non_persistent(self, backend):
        assert backend.map_topic('response:tg:librarian') == \
            'non-persistent://tg/response/librarian'

    def test_passthrough_pulsar_uri(self, backend):
        uri = 'persistent://tg/flow/something'
        assert backend.map_topic(uri) == uri

    def test_invalid_format_raises(self, backend):
        with pytest.raises(ValueError, match="Invalid queue format"):
            backend.map_topic('bad-format')

    def test_invalid_class_raises(self, backend):
        with pytest.raises(ValueError, match="Invalid queue class"):
            backend.map_topic('unknown:tg:topic')

    def test_custom_topicspace(self, backend):
        assert backend.map_topic('flow:prod:my-queue') == \
            'persistent://prod/flow/my-queue'


class TestGetPubsubDispatch:

    def test_unknown_backend_raises(self):
        with pytest.raises(ValueError, match="Unknown pub/sub backend"):
            get_pubsub(pubsub_backend='redis')


class TestAddPubsubArgs:

    def test_standalone_defaults_to_localhost(self):
        parser = argparse.ArgumentParser()
        add_pubsub_args(parser, standalone=True)
        args = parser.parse_args([])
        assert args.pulsar_host == 'pulsar://localhost:6650'
        assert args.pulsar_listener == 'localhost'

    def test_non_standalone_defaults_to_container(self):
        parser = argparse.ArgumentParser()
        add_pubsub_args(parser, standalone=False)
        args = parser.parse_args([])
        assert 'pulsar:6650' in args.pulsar_host
        assert args.pulsar_listener is None

    def test_cli_override_respected(self):
        parser = argparse.ArgumentParser()
        add_pubsub_args(parser, standalone=True)
        args = parser.parse_args(['--pulsar-host', 'pulsar://custom:6650'])
        assert args.pulsar_host == 'pulsar://custom:6650'

    def test_pubsub_backend_default(self):
        parser = argparse.ArgumentParser()
        add_pubsub_args(parser)
        args = parser.parse_args([])
        assert args.pubsub_backend == 'pulsar'


class TestQueueDefinitions:
    """Verify the actual queue constants produce correct names."""

    def test_config_request(self):
        from trustgraph.schema.services.config import config_request_queue
        assert config_request_queue == 'request:tg:config'

    def test_config_response(self):
        from trustgraph.schema.services.config import config_response_queue
        assert config_response_queue == 'response:tg:config'

    def test_config_push(self):
        from trustgraph.schema.services.config import config_push_queue
        assert config_push_queue == 'state:tg:config'

    def test_librarian_request_is_persistent(self):
        from trustgraph.schema.services.library import librarian_request_queue
        assert librarian_request_queue.startswith('flow:')

    def test_knowledge_request(self):
        from trustgraph.schema.knowledge.knowledge import knowledge_request_queue
        assert knowledge_request_queue == 'request:tg:knowledge'
