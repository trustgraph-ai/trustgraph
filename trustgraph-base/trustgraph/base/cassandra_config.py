"""
Cassandra configuration utilities for standardized parameter handling.

Provides consistent Cassandra configuration across all TrustGraph processors,
including command-line arguments, environment variables, and defaults.
"""

import os
import argparse
from typing import Optional, Tuple, List, Any


def get_cassandra_defaults() -> dict:
    """
    Get default Cassandra configuration values from environment variables or fallback defaults.
    
    Returns:
        dict: Dictionary with 'host', 'username', and 'password' keys
    """
    return {
        'host': os.getenv('CASSANDRA_HOST', 'cassandra'),
        'username': os.getenv('CASSANDRA_USERNAME'),
        'password': os.getenv('CASSANDRA_PASSWORD')
    }


def add_cassandra_args(parser: argparse.ArgumentParser) -> None:
    """
    Add standardized Cassandra configuration arguments to an argument parser.
    
    Shows environment variable values in help text when they are set.
    Password values are never displayed for security.
    
    Args:
        parser: ArgumentParser instance to add arguments to
    """
    defaults = get_cassandra_defaults()
    
    # Format help text with environment variable indication
    host_help = f"Cassandra host list, comma-separated (default: {defaults['host']})"
    if 'CASSANDRA_HOST' in os.environ:
        host_help += " [from CASSANDRA_HOST]"
    
    username_help = "Cassandra username"
    if defaults['username']:
        username_help += f" (default: {defaults['username']})"
        if 'CASSANDRA_USERNAME' in os.environ:
            username_help += " [from CASSANDRA_USERNAME]"
    
    password_help = "Cassandra password"
    if defaults['password']:
        # Never show actual password value
        password_help += " (default: <set>)"
        if 'CASSANDRA_PASSWORD' in os.environ:
            password_help += " [from CASSANDRA_PASSWORD]"
    
    parser.add_argument(
        '--cassandra-host',
        default=defaults['host'],
        help=host_help
    )
    
    parser.add_argument(
        '--cassandra-username',
        default=defaults['username'],
        help=username_help
    )
    
    parser.add_argument(
        '--cassandra-password',
        default=defaults['password'],
        help=password_help
    )


def resolve_cassandra_config(
    args: Optional[Any] = None,
    host: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None
) -> Tuple[List[str], Optional[str], Optional[str]]:
    """
    Resolve Cassandra configuration from various sources.
    
    Can accept either argparse args object or explicit parameters.
    Converts host string to list format for Cassandra driver.
    
    Args:
        args: Optional argparse namespace with cassandra_host, cassandra_username, cassandra_password
        host: Optional explicit host parameter (overrides args)
        username: Optional explicit username parameter (overrides args)
        password: Optional explicit password parameter (overrides args)
    
    Returns:
        tuple: (hosts_list, username, password)
    """
    # If args provided, extract values
    if args is not None:
        host = host or getattr(args, 'cassandra_host', None)
        username = username or getattr(args, 'cassandra_username', None)
        password = password or getattr(args, 'cassandra_password', None)
    
    # Apply defaults if still None
    defaults = get_cassandra_defaults()
    host = host or defaults['host']
    username = username or defaults['username']
    password = password or defaults['password']
    
    # Convert host string to list
    if isinstance(host, str):
        hosts = [h.strip() for h in host.split(',') if h.strip()]
    else:
        hosts = host
    
    return hosts, username, password


def get_cassandra_config_from_params(params: dict) -> Tuple[List[str], Optional[str], Optional[str]]:
    """
    Extract and resolve Cassandra configuration from a parameters dictionary.
    
    Handles both old graph_* and new cassandra_* parameter names for backward compatibility.
    
    Args:
        params: Dictionary of parameters that may contain Cassandra configuration
    
    Returns:
        tuple: (hosts_list, username, password)
    """
    # Check for new parameter names first
    host = params.get('cassandra_host')
    username = params.get('cassandra_username')
    password = params.get('cassandra_password')
    
    # Fall back to old graph_* names for backward compatibility
    if not host:
        host = params.get('graph_host')
    if not username:
        username = params.get('graph_username', params.get('cassandra_user'))
    if not password:
        password = params.get('graph_password')
    
    # Use resolve function to handle defaults and list conversion
    return resolve_cassandra_config(host=host, username=username, password=password)