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
        dict: Dictionary with 'host', 'username', 'password', and 'keyspace' keys
    """
    return {
        'host': os.getenv('CASSANDRA_HOST', 'cassandra'),
        'username': os.getenv('CASSANDRA_USERNAME'),
        'password': os.getenv('CASSANDRA_PASSWORD'),
        'keyspace': os.getenv('CASSANDRA_KEYSPACE'),
        'replication_factor': int(os.getenv('CASSANDRA_REPLICATION_FACTOR', '1'))
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

    keyspace_help = "Cassandra keyspace (default: service-specific)"
    if defaults['keyspace']:
        keyspace_help = f"Cassandra keyspace (default: {defaults['keyspace']})"
        if 'CASSANDRA_KEYSPACE' in os.environ:
            keyspace_help += " [from CASSANDRA_KEYSPACE]"

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

    parser.add_argument(
        '--cassandra-keyspace',
        default=defaults['keyspace'],
        help=keyspace_help
    )

    replication_factor_help = f"Cassandra keyspace replication factor (default: {defaults['replication_factor']})"
    if 'CASSANDRA_REPLICATION_FACTOR' in os.environ:
        replication_factor_help += " [from CASSANDRA_REPLICATION_FACTOR]"

    parser.add_argument(
        '--cassandra-replication-factor',
        type=int,
        default=defaults['replication_factor'],
        help=replication_factor_help
    )


def resolve_cassandra_config(
    args: Optional[Any] = None,
    host: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    default_keyspace: Optional[str] = None
) -> Tuple[List[str], Optional[str], Optional[str], Optional[str], int]:
    """
    Resolve Cassandra configuration from various sources.

    Can accept either argparse args object or explicit parameters.
    Converts host string to list format for Cassandra driver.

    Args:
        args: Optional argparse namespace with cassandra_host, cassandra_username, cassandra_password, cassandra_keyspace, cassandra_replication_factor
        host: Optional explicit host parameter (overrides args)
        username: Optional explicit username parameter (overrides args)
        password: Optional explicit password parameter (overrides args)
        default_keyspace: Optional default keyspace if not specified elsewhere

    Returns:
        tuple: (hosts_list, username, password, keyspace, replication_factor)
    """
    # If args provided, extract values
    keyspace = None
    replication_factor = 1
    if args is not None:
        host = host or getattr(args, 'cassandra_host', None)
        username = username or getattr(args, 'cassandra_username', None)
        password = password or getattr(args, 'cassandra_password', None)
        keyspace = getattr(args, 'cassandra_keyspace', None)
        replication_factor = getattr(args, 'cassandra_replication_factor', 1)

    # Apply defaults if still None
    defaults = get_cassandra_defaults()
    host = host or defaults['host']
    username = username or defaults['username']
    password = password or defaults['password']
    keyspace = keyspace or defaults['keyspace'] or default_keyspace
    replication_factor = replication_factor or defaults['replication_factor']

    # Convert host string to list
    if isinstance(host, str):
        hosts = [h.strip() for h in host.split(',') if h.strip()]
    else:
        hosts = host

    return hosts, username, password, keyspace, replication_factor


def get_cassandra_config_from_params(
    params: dict,
    default_keyspace: Optional[str] = None
) -> Tuple[List[str], Optional[str], Optional[str], Optional[str], int]:
    """
    Extract and resolve Cassandra configuration from a parameters dictionary.

    Args:
        params: Dictionary of parameters that may contain Cassandra configuration
        default_keyspace: Optional default keyspace if not specified in params

    Returns:
        tuple: (hosts_list, username, password, keyspace, replication_factor)
    """
    host = params.get('cassandra_host')
    username = params.get('cassandra_username')
    password = params.get('cassandra_password')

    return resolve_cassandra_config(
        host=host,
        username=username,
        password=password,
        default_keyspace=default_keyspace
    )