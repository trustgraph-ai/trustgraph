"""
Unit tests for Cassandra configuration helper module.

Tests configuration resolution, environment variable handling,
command-line argument parsing, and backward compatibility.
"""

import argparse
import os
import pytest
from unittest.mock import patch

from trustgraph.base.cassandra_config import (
    get_cassandra_defaults,
    add_cassandra_args,
    resolve_cassandra_config,
    get_cassandra_config_from_params
)


class TestGetCassandraDefaults:
    """Test the get_cassandra_defaults function."""
    
    def test_defaults_with_no_env_vars(self):
        """Test defaults when no environment variables are set."""
        with patch.dict(os.environ, {}, clear=True):
            defaults = get_cassandra_defaults()
            
            assert defaults['host'] == 'cassandra'
            assert defaults['username'] is None
            assert defaults['password'] is None
    
    def test_defaults_with_env_vars(self):
        """Test defaults when environment variables are set."""
        env_vars = {
            'CASSANDRA_HOST': 'env-host1,env-host2',
            'CASSANDRA_USERNAME': 'env-user',
            'CASSANDRA_PASSWORD': 'env-pass'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            defaults = get_cassandra_defaults()
            
            assert defaults['host'] == 'env-host1,env-host2'
            assert defaults['username'] == 'env-user'
            assert defaults['password'] == 'env-pass'
    
    def test_partial_env_vars(self):
        """Test defaults when only some environment variables are set."""
        env_vars = {
            'CASSANDRA_HOST': 'partial-host',
            'CASSANDRA_USERNAME': 'partial-user'
            # CASSANDRA_PASSWORD not set
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            defaults = get_cassandra_defaults()
            
            assert defaults['host'] == 'partial-host'
            assert defaults['username'] == 'partial-user'
            assert defaults['password'] is None


class TestAddCassandraArgs:
    """Test the add_cassandra_args function."""
    
    def test_basic_args_added(self):
        """Test that all three arguments are added to parser."""
        parser = argparse.ArgumentParser()
        add_cassandra_args(parser)
        
        # Parse empty args to check defaults
        args = parser.parse_args([])
        
        assert hasattr(args, 'cassandra_host')
        assert hasattr(args, 'cassandra_username')
        assert hasattr(args, 'cassandra_password')
    
    def test_help_text_no_env_vars(self):
        """Test help text when no environment variables are set."""
        with patch.dict(os.environ, {}, clear=True):
            parser = argparse.ArgumentParser()
            add_cassandra_args(parser)
            
            help_text = parser.format_help()
            
            assert 'Cassandra host list, comma-separated (default:' in help_text
            assert 'cassandra)' in help_text
            assert 'Cassandra username' in help_text
            assert 'Cassandra password' in help_text
            assert '[from CASSANDRA_HOST]' not in help_text
    
    def test_help_text_with_env_vars(self):
        """Test help text when environment variables are set."""
        env_vars = {
            'CASSANDRA_HOST': 'help-host1,help-host2',
            'CASSANDRA_USERNAME': 'help-user',
            'CASSANDRA_PASSWORD': 'help-pass'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            parser = argparse.ArgumentParser()
            add_cassandra_args(parser)
            
            help_text = parser.format_help()
            
            # Help text may have line breaks - argparse breaks long lines
            # So check for the components that should be there
            assert 'help-' in help_text and 'host1' in help_text
            assert 'help-host2' in help_text
            # Check key components (may be split across lines by argparse)
            assert '[from CASSANDRA_HOST]' in help_text
            assert '(default: help-user)' in help_text
            assert '[from' in help_text and 'CASSANDRA_USERNAME]' in help_text
            assert '(default: <set>)' in help_text  # Password hidden
            assert '[from' in help_text and 'CASSANDRA_PASSWORD]' in help_text
            assert 'help-pass' not in help_text  # Password value not shown
    
    def test_command_line_override(self):
        """Test that command-line arguments override environment variables."""
        env_vars = {
            'CASSANDRA_HOST': 'env-host',
            'CASSANDRA_USERNAME': 'env-user',
            'CASSANDRA_PASSWORD': 'env-pass'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            parser = argparse.ArgumentParser()
            add_cassandra_args(parser)
            
            args = parser.parse_args([
                '--cassandra-host', 'cli-host',
                '--cassandra-username', 'cli-user',
                '--cassandra-password', 'cli-pass'
            ])
            
            assert args.cassandra_host == 'cli-host'
            assert args.cassandra_username == 'cli-user'
            assert args.cassandra_password == 'cli-pass'


class TestResolveCassandraConfig:
    """Test the resolve_cassandra_config function."""
    
    def test_default_configuration(self):
        """Test resolution with no parameters or environment variables."""
        with patch.dict(os.environ, {}, clear=True):
            hosts, username, password = resolve_cassandra_config()
            
            assert hosts == ['cassandra']
            assert username is None
            assert password is None
    
    def test_environment_variable_resolution(self):
        """Test resolution from environment variables."""
        env_vars = {
            'CASSANDRA_HOST': 'env1,env2,env3',
            'CASSANDRA_USERNAME': 'env-user',
            'CASSANDRA_PASSWORD': 'env-pass'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            hosts, username, password = resolve_cassandra_config()
            
            assert hosts == ['env1', 'env2', 'env3']
            assert username == 'env-user'
            assert password == 'env-pass'
    
    def test_explicit_parameter_override(self):
        """Test that explicit parameters override environment variables."""
        env_vars = {
            'CASSANDRA_HOST': 'env-host',
            'CASSANDRA_USERNAME': 'env-user',
            'CASSANDRA_PASSWORD': 'env-pass'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            hosts, username, password = resolve_cassandra_config(
                host='explicit-host',
                username='explicit-user',
                password='explicit-pass'
            )
            
            assert hosts == ['explicit-host']
            assert username == 'explicit-user'
            assert password == 'explicit-pass'
    
    def test_host_list_parsing(self):
        """Test different host list formats."""
        # Single host
        hosts, _, _ = resolve_cassandra_config(host='single-host')
        assert hosts == ['single-host']
        
        # Multiple hosts with spaces
        hosts, _, _ = resolve_cassandra_config(host='host1, host2 ,host3')
        assert hosts == ['host1', 'host2', 'host3']
        
        # Empty elements filtered out
        hosts, _, _ = resolve_cassandra_config(host='host1,,host2,')
        assert hosts == ['host1', 'host2']
        
        # Already a list
        hosts, _, _ = resolve_cassandra_config(host=['list-host1', 'list-host2'])
        assert hosts == ['list-host1', 'list-host2']
    
    def test_args_object_resolution(self):
        """Test resolution from argparse args object."""
        # Mock args object
        class MockArgs:
            cassandra_host = 'args-host1,args-host2'
            cassandra_username = 'args-user'
            cassandra_password = 'args-pass'
        
        args = MockArgs()
        hosts, username, password = resolve_cassandra_config(args)
        
        assert hosts == ['args-host1', 'args-host2']
        assert username == 'args-user'
        assert password == 'args-pass'
    
    def test_partial_args_with_env_fallback(self):
        """Test args object with missing attributes falls back to environment."""
        env_vars = {
            'CASSANDRA_HOST': 'env-host',
            'CASSANDRA_USERNAME': 'env-user',
            'CASSANDRA_PASSWORD': 'env-pass'
        }
        
        # Args object with only some attributes
        class PartialArgs:
            cassandra_host = 'args-host'
            # Missing cassandra_username and cassandra_password
        
        with patch.dict(os.environ, env_vars, clear=True):
            args = PartialArgs()
            hosts, username, password = resolve_cassandra_config(args)
            
            assert hosts == ['args-host']  # From args
            assert username == 'env-user'  # From env
            assert password == 'env-pass'  # From env


class TestGetCassandraConfigFromParams:
    """Test the get_cassandra_config_from_params function."""
    
    def test_new_parameter_names(self):
        """Test with new cassandra_* parameter names."""
        params = {
            'cassandra_host': 'new-host1,new-host2',
            'cassandra_username': 'new-user',
            'cassandra_password': 'new-pass'
        }
        
        hosts, username, password = get_cassandra_config_from_params(params)
        
        assert hosts == ['new-host1', 'new-host2']
        assert username == 'new-user'
        assert password == 'new-pass'
    
    def test_no_backward_compatibility_graph_params(self):
        """Test that old graph_* parameter names are no longer supported."""
        params = {
            'graph_host': 'old-host',
            'graph_username': 'old-user',
            'graph_password': 'old-pass'
        }
        
        hosts, username, password = get_cassandra_config_from_params(params)
        
        # Should use defaults since graph_* params are not recognized
        assert hosts == ['cassandra']  # Default
        assert username is None
        assert password is None
    
    def test_no_old_cassandra_user_compatibility(self):
        """Test that cassandra_user is no longer supported (must be cassandra_username)."""
        params = {
            'cassandra_host': 'compat-host',
            'cassandra_user': 'compat-user',  # Old name - not supported
            'cassandra_password': 'compat-pass'
        }
        
        hosts, username, password = get_cassandra_config_from_params(params)
        
        assert hosts == ['compat-host']
        assert username is None  # cassandra_user is not recognized
        assert password == 'compat-pass'
    
    def test_only_new_parameters_work(self):
        """Test that only new parameter names are recognized."""
        params = {
            'cassandra_host': 'new-host',
            'graph_host': 'old-host',
            'cassandra_username': 'new-user',
            'graph_username': 'old-user',
            'cassandra_user': 'older-user',
            'cassandra_password': 'new-pass',
            'graph_password': 'old-pass'
        }
        
        hosts, username, password = get_cassandra_config_from_params(params)
        
        assert hosts == ['new-host']  # Only cassandra_* params work
        assert username == 'new-user'  # Only cassandra_* params work
        assert password == 'new-pass'  # Only cassandra_* params work
    
    def test_empty_params_with_env_fallback(self):
        """Test that empty params falls back to environment variables."""
        env_vars = {
            'CASSANDRA_HOST': 'fallback-host1,fallback-host2',
            'CASSANDRA_USERNAME': 'fallback-user',
            'CASSANDRA_PASSWORD': 'fallback-pass'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            params = {}
            hosts, username, password = get_cassandra_config_from_params(params)
            
            assert hosts == ['fallback-host1', 'fallback-host2']
            assert username == 'fallback-user'
            assert password == 'fallback-pass'


class TestConfigurationPriority:
    """Test the overall configuration priority: CLI > env vars > defaults."""
    
    def test_full_priority_chain(self):
        """Test complete priority chain with all sources present."""
        env_vars = {
            'CASSANDRA_HOST': 'env-host',
            'CASSANDRA_USERNAME': 'env-user',
            'CASSANDRA_PASSWORD': 'env-pass'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            # CLI args should override everything
            hosts, username, password = resolve_cassandra_config(
                host='cli-host',
                username='cli-user',
                password='cli-pass'
            )
            
            assert hosts == ['cli-host']
            assert username == 'cli-user'
            assert password == 'cli-pass'
    
    def test_partial_cli_with_env_fallback(self):
        """Test partial CLI args with environment variable fallback."""
        env_vars = {
            'CASSANDRA_HOST': 'env-host',
            'CASSANDRA_USERNAME': 'env-user',
            'CASSANDRA_PASSWORD': 'env-pass'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            # Only provide host via CLI
            hosts, username, password = resolve_cassandra_config(
                host='cli-host'
                # username and password not provided
            )
            
            assert hosts == ['cli-host']      # From CLI
            assert username == 'env-user'    # From env
            assert password == 'env-pass'    # From env
    
    def test_no_config_defaults(self):
        """Test that defaults are used when no configuration is provided."""
        with patch.dict(os.environ, {}, clear=True):
            hosts, username, password = resolve_cassandra_config()
            
            assert hosts == ['cassandra']  # Default
            assert username is None       # Default
            assert password is None       # Default


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_host_string(self):
        """Test handling of empty host string falls back to default."""
        hosts, _, _ = resolve_cassandra_config(host='')
        assert hosts == ['cassandra']  # Falls back to default
    
    def test_whitespace_only_host(self):
        """Test handling of whitespace-only host string."""
        hosts, _, _ = resolve_cassandra_config(host='   ')
        assert hosts == []  # Empty after stripping whitespace
    
    def test_none_values_preserved(self):
        """Test that None values are preserved correctly."""
        hosts, username, password = resolve_cassandra_config(
            host=None,
            username=None,
            password=None
        )
        
        # Should fall back to defaults
        assert hosts == ['cassandra']
        assert username is None
        assert password is None
    
    def test_mixed_none_and_values(self):
        """Test mixing None and actual values."""
        hosts, username, password = resolve_cassandra_config(
            host='mixed-host',
            username=None,
            password='mixed-pass'
        )
        
        assert hosts == ['mixed-host']
        assert username is None  # Stays None
        assert password == 'mixed-pass'