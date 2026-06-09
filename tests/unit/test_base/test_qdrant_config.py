
import os
import pytest
from unittest.mock import patch

from trustgraph.base.qdrant_config import (
    get_qdrant_defaults,
    resolve_qdrant_config,
)


class TestGetQdrantDefaults:

    def test_defaults_with_no_env_vars(self):
        with patch.dict(os.environ, {}, clear=True):
            defaults = get_qdrant_defaults()
            assert defaults['url'] == 'http://localhost:6333'
            assert defaults['api_key'] is None
            assert defaults['replication_factor'] == 1
            assert defaults['shard_number'] == 1

    def test_defaults_from_env(self):
        env = {
            'QDRANT_URL': 'http://qdrant:6333',
            'QDRANT_API_KEY': 'secret',
            'QDRANT_REPLICATION_FACTOR': '3',
            'QDRANT_SHARD_NUMBER': '5',
        }
        with patch.dict(os.environ, env, clear=True):
            defaults = get_qdrant_defaults()
            assert defaults['url'] == 'http://qdrant:6333'
            assert defaults['api_key'] == 'secret'
            assert defaults['replication_factor'] == 3
            assert defaults['shard_number'] == 5


class TestResolveQdrantConfig:

    def test_defaults(self):
        with patch.dict(os.environ, {}, clear=True):
            url, api_key, rf, sn = resolve_qdrant_config()
            assert url == 'http://localhost:6333'
            assert api_key is None
            assert rf == 1
            assert sn == 1

    def test_explicit_kwargs(self):
        with patch.dict(os.environ, {}, clear=True):
            url, api_key, rf, sn = resolve_qdrant_config(
                url='http://custom:6333',
                api_key='key',
                replication_factor=3,
                shard_number=5,
            )
            assert url == 'http://custom:6333'
            assert api_key == 'key'
            assert rf == 3
            assert sn == 5

    def test_kwargs_override_env(self):
        env = {
            'QDRANT_URL': 'http://env:6333',
            'QDRANT_REPLICATION_FACTOR': '10',
            'QDRANT_SHARD_NUMBER': '10',
        }
        with patch.dict(os.environ, env, clear=True):
            url, _, rf, sn = resolve_qdrant_config(
                url='http://explicit:6333',
                replication_factor=3,
                shard_number=5,
            )
            assert url == 'http://explicit:6333'
            assert rf == 3
            assert sn == 5

    def test_env_fallback_when_kwargs_none(self):
        env = {
            'QDRANT_URL': 'http://env:6333',
            'QDRANT_REPLICATION_FACTOR': '3',
            'QDRANT_SHARD_NUMBER': '5',
        }
        with patch.dict(os.environ, env, clear=True):
            url, _, rf, sn = resolve_qdrant_config()
            assert url == 'http://env:6333'
            assert rf == 3
            assert sn == 5

    def test_params_dict_path(self):
        with patch.dict(os.environ, {}, clear=True):
            params = {
                'store_uri': 'http://params:6333',
                'api_key': 'pkey',
                'qdrant_replication_factor': 3,
                'qdrant_shard_number': 5,
            }
            url, api_key, rf, sn = resolve_qdrant_config(
                url=params.get('store_uri'),
                api_key=params.get('api_key'),
                replication_factor=params.get('qdrant_replication_factor'),
                shard_number=params.get('qdrant_shard_number'),
            )
            assert url == 'http://params:6333'
            assert api_key == 'pkey'
            assert rf == 3
            assert sn == 5

    def test_params_dict_overrides_env(self):
        env = {
            'QDRANT_REPLICATION_FACTOR': '10',
            'QDRANT_SHARD_NUMBER': '10',
        }
        with patch.dict(os.environ, env, clear=True):
            params = {
                'qdrant_replication_factor': 3,
                'qdrant_shard_number': 5,
            }
            _, _, rf, sn = resolve_qdrant_config(
                replication_factor=params.get('qdrant_replication_factor'),
                shard_number=params.get('qdrant_shard_number'),
            )
            assert rf == 3
            assert sn == 5

    def test_params_dict_missing_falls_to_env(self):
        env = {
            'QDRANT_REPLICATION_FACTOR': '3',
            'QDRANT_SHARD_NUMBER': '5',
        }
        with patch.dict(os.environ, env, clear=True):
            params = {}
            _, _, rf, sn = resolve_qdrant_config(
                replication_factor=params.get('qdrant_replication_factor'),
                shard_number=params.get('qdrant_shard_number'),
            )
            assert rf == 3
            assert sn == 5
