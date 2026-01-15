"""
TrustGraph Configuration Management

This module provides interfaces for managing TrustGraph configuration settings,
including retrieving, updating, and deleting configuration values.
"""

import logging

from . exceptions import *
from . types import ConfigValue

logger = logging.getLogger(__name__)

class Config:
    """
    Configuration management client.

    Provides methods for managing TrustGraph configuration settings across
    different types (llm, embedding, etc.), with support for get, put, delete,
    and list operations.
    """

    def __init__(self, api):
        """
        Initialize Config client.

        Args:
            api: Parent Api instance for making requests
        """
        self.api = api

    def request(self, request):
        """
        Make a configuration-scoped API request.

        Args:
            request: Request payload dictionary

        Returns:
            dict: Response object
        """
        return self.api.request("config", request)

    def get(self, keys):
        """
        Get configuration values for specified keys.

        Retrieves the configuration values for one or more configuration keys.

        Args:
            keys: List of ConfigKey objects specifying which values to retrieve

        Returns:
            list[ConfigValue]: List of configuration values

        Raises:
            ProtocolException: If response format is invalid

        Example:
            ```python
            from trustgraph.api import ConfigKey

            config = api.config()

            # Get specific configuration values
            values = config.get([
                ConfigKey(type="llm", key="model"),
                ConfigKey(type="llm", key="temperature"),
                ConfigKey(type="embedding", key="model")
            ])

            for val in values:
                print(f"{val.type}.{val.key} = {val.value}")
            ```
        """

        # The input consists of system and prompt strings
        input = {
            "operation": "get",
            "keys": [
                { "type": k.type, "key": k.key }
                for k in keys
            ]
        }

        object = self.request(input)

        try:
            return [
                ConfigValue(
                    type = v["type"],
                    key = v["key"],
                    value = v["value"]
                )
                for v in object["values"]
            ]
        except Exception as e:
            logger.error("Failed to parse config get response", exc_info=True)
            raise ProtocolException("Response not formatted correctly")

    def put(self, values):
        """
        Set configuration values.

        Updates or creates configuration values for the specified keys.

        Args:
            values: List of ConfigValue objects with type, key, and value

        Example:
            ```python
            from trustgraph.api import ConfigValue

            config = api.config()

            # Set configuration values
            config.put([
                ConfigValue(type="llm", key="model", value="gpt-4"),
                ConfigValue(type="llm", key="temperature", value="0.7"),
                ConfigValue(type="embedding", key="model", value="text-embedding-3-small")
            ])
            ```
        """

        # The input consists of system and prompt strings
        input = {
            "operation": "put",
            "values": [
                { "type": v.type, "key": v.key, "value": v.value }
                for v in values
            ]
        }

        self.request(input)

    def delete(self, keys):
        """
        Delete configuration values.

        Removes configuration values for the specified keys.

        Args:
            keys: List of ConfigKey objects specifying which values to delete

        Example:
            ```python
            from trustgraph.api import ConfigKey

            config = api.config()

            # Delete configuration values
            config.delete([
                ConfigKey(type="llm", key="old-setting"),
                ConfigKey(type="embedding", key="deprecated")
            ])
            ```
        """

        # The input consists of system and prompt strings
        input = {
            "operation": "delete",
            "keys": [
                { "type": v.type, "key": v.key }
                for v in keys
            ]
        }

        self.request(input)

    def list(self, type):
        """
        List all configuration keys for a given type.

        Retrieves a list of all configuration key names within a specific
        configuration type.

        Args:
            type: Configuration type (e.g., "llm", "embedding", "storage")

        Returns:
            list[str]: List of configuration key names

        Example:
            ```python
            config = api.config()

            # List all LLM configuration keys
            llm_keys = config.list(type="llm")
            print(f"LLM configuration keys: {llm_keys}")

            # List all embedding configuration keys
            embedding_keys = config.list(type="embedding")
            print(f"Embedding configuration keys: {embedding_keys}")
            ```
        """

        # The input consists of system and prompt strings
        input = {
            "operation": "list",
            "type": type,
        }

        return self.request(input)["directory"]

    def get_values(self, type):
        """
        Get all configuration values for a given type.

        Retrieves all configuration key-value pairs within a specific
        configuration type.

        Args:
            type: Configuration type (e.g., "llm", "embedding", "storage")

        Returns:
            list[ConfigValue]: List of all configuration values for the type

        Raises:
            ProtocolException: If response format is invalid

        Example:
            ```python
            config = api.config()

            # Get all LLM configuration
            llm_config = config.get_values(type="llm")
            for val in llm_config:
                print(f"{val.key} = {val.value}")

            # Get all embedding configuration
            embedding_config = config.get_values(type="embedding")
            for val in embedding_config:
                print(f"{val.key} = {val.value}")
            ```
        """

        # The input consists of system and prompt strings
        input = {
            "operation": "getvalues",
            "type": type,
        }

        object = self.request(input)

        try:
            return [
                ConfigValue(
                    type = v["type"],
                    key = v["key"],
                    value = v["value"]
                )
                for v in object["values"]
            ]
        except:
            raise ProtocolException(f"Response not formatted correctly")

    def all(self):
        """
        Get complete configuration and version.

        Retrieves the entire configuration object along with its version number.

        Returns:
            tuple: (config_dict, version_string) - Complete configuration and version

        Raises:
            ProtocolException: If response format is invalid

        Example:
            ```python
            config = api.config()

            # Get complete configuration
            config_data, version = config.all()

            print(f"Configuration version: {version}")
            print(f"Configuration: {config_data}")
            ```
        """

        # The input consists of system and prompt strings
        input = {
            "operation": "config"
        }

        object = self.request(input)

        try:
            return object["config"], object["version"]
        except:
            raise ProtocolException(f"Response not formatted correctly")

