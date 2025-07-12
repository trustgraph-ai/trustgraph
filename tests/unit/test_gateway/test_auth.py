"""
Tests for Gateway Authentication
"""

import pytest

from trustgraph.gateway.auth import Authenticator


class TestAuthenticator:
    """Test cases for Authenticator class"""

    def test_authenticator_initialization_with_token(self):
        """Test Authenticator initialization with valid token"""
        auth = Authenticator(token="test-token-123")
        
        assert auth.token == "test-token-123"
        assert auth.allow_all is False

    def test_authenticator_initialization_with_allow_all(self):
        """Test Authenticator initialization with allow_all=True"""
        auth = Authenticator(allow_all=True)
        
        assert auth.token is None
        assert auth.allow_all is True

    def test_authenticator_initialization_without_token_raises_error(self):
        """Test Authenticator initialization without token raises RuntimeError"""
        with pytest.raises(RuntimeError, match="Need a token"):
            Authenticator()

    def test_authenticator_initialization_with_empty_token_raises_error(self):
        """Test Authenticator initialization with empty token raises RuntimeError"""
        with pytest.raises(RuntimeError, match="Need a token"):
            Authenticator(token="")

    def test_permitted_with_allow_all_returns_true(self):
        """Test permitted method returns True when allow_all is enabled"""
        auth = Authenticator(allow_all=True)
        
        # Should return True regardless of token or roles
        assert auth.permitted("any-token", []) is True
        assert auth.permitted("different-token", ["admin"]) is True
        assert auth.permitted(None, ["user"]) is True

    def test_permitted_with_matching_token_returns_true(self):
        """Test permitted method returns True with matching token"""
        auth = Authenticator(token="secret-token")
        
        # Should return True when tokens match
        assert auth.permitted("secret-token", []) is True
        assert auth.permitted("secret-token", ["admin", "user"]) is True

    def test_permitted_with_non_matching_token_returns_false(self):
        """Test permitted method returns False with non-matching token"""
        auth = Authenticator(token="secret-token")
        
        # Should return False when tokens don't match
        assert auth.permitted("wrong-token", []) is False
        assert auth.permitted("different-token", ["admin"]) is False
        assert auth.permitted(None, ["user"]) is False

    def test_permitted_with_token_and_allow_all_returns_true(self):
        """Test permitted method with both token and allow_all set"""
        auth = Authenticator(token="test-token", allow_all=True)
        
        # allow_all should take precedence
        assert auth.permitted("any-token", []) is True
        assert auth.permitted("wrong-token", ["admin"]) is True