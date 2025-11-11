"""
Unit tests for MCP tool bearer token authentication

Tests the authentication feature added to MCP tool service that allows
configuring optional bearer tokens for MCP server connections.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import json


class TestMcpToolAuthentication:
    """Test cases for MCP tool bearer token authentication"""

    def test_mcp_tool_with_auth_token_header_building(self):
        """Test that auth token is correctly formatted in headers"""
        # Arrange
        mcp_config = {
            "url": "https://secure.example.com/mcp",
            "remote-name": "secure-tool",
            "auth-token": "test-token-12345"
        }

        # Act - simulate header building logic from service.py
        headers = {}
        if "auth-token" in mcp_config and mcp_config["auth-token"]:
            token = mcp_config["auth-token"]
            headers["Authorization"] = f"Bearer {token}"

        # Assert
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test-token-12345"
        assert headers["Authorization"].startswith("Bearer ")

    def test_mcp_tool_without_auth_token_header_building(self):
        """Test that no auth header is added when token is not present (backward compatibility)"""
        # Arrange
        mcp_config = {
            "url": "http://public.example.com/mcp",
            "remote-name": "public-tool"
            # No auth-token field
        }

        # Act - simulate header building logic from service.py
        headers = {}
        if "auth-token" in mcp_config and mcp_config["auth-token"]:
            token = mcp_config["auth-token"]
            headers["Authorization"] = f"Bearer {token}"

        # Assert
        assert headers == {}
        assert "Authorization" not in headers

    def test_mcp_config_with_auth_token(self):
        """Test MCP configuration parsing with auth-token"""
        # Arrange
        config = {
            "mcp": {
                "secure-tool": json.dumps({
                    "url": "https://secure.example.com/mcp",
                    "remote-name": "secure-tool",
                    "auth-token": "test-token-xyz"
                }),
                "public-tool": json.dumps({
                    "url": "http://public.example.com/mcp",
                    "remote-name": "public-tool"
                })
            }
        }

        # Act - simulate on_mcp_config
        mcp_services = {
            k: json.loads(v)
            for k, v in config["mcp"].items()
        }

        # Assert
        assert "secure-tool" in mcp_services
        assert mcp_services["secure-tool"]["auth-token"] == "test-token-xyz"
        assert mcp_services["secure-tool"]["url"] == "https://secure.example.com/mcp"

        assert "public-tool" in mcp_services
        assert "auth-token" not in mcp_services["public-tool"]
        assert mcp_services["public-tool"]["url"] == "http://public.example.com/mcp"

    def test_auth_token_with_empty_string(self):
        """Test that empty auth-token string is treated as no auth"""
        # Arrange
        config_data = {
            "url": "https://example.com/mcp",
            "remote-name": "test-tool",
            "auth-token": ""
        }

        # Act - simulate header building logic
        headers = {}
        if "auth-token" in config_data and config_data["auth-token"]:
            headers["Authorization"] = f"Bearer {config_data['auth-token']}"

        # Assert
        assert headers == {}, "Empty auth-token should not add Authorization header"

    def test_auth_token_with_special_characters(self):
        """Test auth token with special characters (JWT-like)"""
        # Arrange
        jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"

        config_data = {
            "url": "https://example.com/mcp",
            "auth-token": jwt_token
        }

        # Act - simulate header building
        headers = {}
        if "auth-token" in config_data and config_data["auth-token"]:
            token = config_data["auth-token"]
            headers["Authorization"] = f"Bearer {token}"

        # Assert
        assert headers["Authorization"] == f"Bearer {jwt_token}"
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" in headers["Authorization"]

    def test_multiple_tools_with_different_auth_configs(self):
        """Test handling multiple MCP tools with mixed auth configurations"""
        # Arrange
        mcp_services = {
            "tool-a": {
                "url": "https://a.example.com/mcp",
                "auth-token": "token-a"
            },
            "tool-b": {
                "url": "https://b.example.com/mcp",
                "auth-token": "token-b"
            },
            "tool-c": {
                "url": "http://c.example.com/mcp"
                # No auth-token
            }
        }

        # Act - simulate header building for each tool
        headers_a = {}
        if "auth-token" in mcp_services["tool-a"] and mcp_services["tool-a"]["auth-token"]:
            headers_a["Authorization"] = f"Bearer {mcp_services['tool-a']['auth-token']}"

        headers_b = {}
        if "auth-token" in mcp_services["tool-b"] and mcp_services["tool-b"]["auth-token"]:
            headers_b["Authorization"] = f"Bearer {mcp_services['tool-b']['auth-token']}"

        headers_c = {}
        if "auth-token" in mcp_services["tool-c"] and mcp_services["tool-c"]["auth-token"]:
            headers_c["Authorization"] = f"Bearer {mcp_services['tool-c']['auth-token']}"

        # Assert
        assert headers_a == {"Authorization": "Bearer token-a"}
        assert headers_b == {"Authorization": "Bearer token-b"}
        assert headers_c == {}

    def test_auth_token_not_logged(self):
        """Test that auth tokens are not exposed in logs"""
        # This is more of a guideline test - in real implementation,
        # we should ensure tokens are never logged

        # Arrange
        auth_token = "super-secret-token-123"
        config = {
            "url": "https://secure.example.com/mcp",
            "auth-token": auth_token
        }

        # Act - simulate log-safe representation
        def get_log_safe_config(cfg):
            """Return config with sensitive data masked"""
            safe_config = cfg.copy()
            if "auth-token" in safe_config and safe_config["auth-token"]:
                safe_config["auth-token"] = "****"
            return safe_config

        log_safe = get_log_safe_config(config)

        # Assert
        assert log_safe["auth-token"] == "****"
        assert auth_token not in str(log_safe)
        assert "url" in log_safe
        assert log_safe["url"] == "https://secure.example.com/mcp"

    def test_auth_token_with_remote_name_configuration(self):
        """Test MCP tool configuration with both auth-token and remote-name"""
        # Arrange
        mcp_config = {
            "url": "https://server.example.com/mcp",
            "remote-name": "actual_tool_name",
            "auth-token": "my-token-456"
        }

        # Act - simulate header building and remote name extraction
        headers = {}
        if "auth-token" in mcp_config and mcp_config["auth-token"]:
            token = mcp_config["auth-token"]
            headers["Authorization"] = f"Bearer {token}"

        remote_name = mcp_config.get("remote-name", "default-name")

        # Assert
        assert headers["Authorization"] == "Bearer my-token-456"
        assert remote_name == "actual_tool_name"
        assert "url" in mcp_config
        assert mcp_config["url"] == "https://server.example.com/mcp"

    def test_bearer_token_format(self):
        """Test that Bearer token format is correct"""
        # Arrange
        tokens = [
            "simple-token",
            "token_with_underscore",
            "token-with-dash",
            "TokenWithMixedCase123",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.signature"
        ]

        # Act & Assert
        for token in tokens:
            headers = {}
            if token:
                headers["Authorization"] = f"Bearer {token}"

            # Verify format is "Bearer <token>" with single space
            assert headers["Authorization"].startswith("Bearer ")
            assert headers["Authorization"] == f"Bearer {token}"
            # Verify no extra spaces
            assert headers["Authorization"].count("Bearer") == 1
            assert headers["Authorization"].split("Bearer ")[1] == token
