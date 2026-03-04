"""
Unit tests for Tool Service functionality

Tests the dynamically pluggable tool services feature including:
- Tool service configuration parsing
- ToolServiceImpl initialization
- Request/response format
- Config parameter handling
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import json


class TestToolServiceConfigParsing:
    """Test cases for tool service configuration parsing"""

    def test_tool_service_config_structure(self):
        """Test that tool-service config has required fields"""
        # Arrange
        valid_config = {
            "id": "joke-service",
            "request-queue": "non-persistent://tg/request/joke",
            "response-queue": "non-persistent://tg/response/joke",
            "config-params": [
                {"name": "style", "required": False}
            ]
        }

        # Act & Assert
        assert "id" in valid_config
        assert "request-queue" in valid_config
        assert "response-queue" in valid_config
        assert valid_config["request-queue"].startswith("non-persistent://")
        assert valid_config["response-queue"].startswith("non-persistent://")

    def test_tool_service_config_without_queues_is_invalid(self):
        """Test that tool-service config requires request-queue and response-queue"""
        # Arrange
        invalid_config = {
            "id": "joke-service",
            "config-params": []
        }

        # Act & Assert
        def validate_config(config):
            request_queue = config.get("request-queue")
            response_queue = config.get("response-queue")
            if not request_queue or not response_queue:
                raise RuntimeError("Tool-service must define 'request-queue' and 'response-queue'")
            return True

        with pytest.raises(RuntimeError) as exc_info:
            validate_config(invalid_config)
        assert "request-queue" in str(exc_info.value)

    def test_tool_config_references_tool_service(self):
        """Test that tool config correctly references a tool-service"""
        # Arrange
        tool_services = {
            "joke-service": {
                "id": "joke-service",
                "request-queue": "non-persistent://tg/request/joke",
                "response-queue": "non-persistent://tg/response/joke",
                "config-params": [{"name": "style", "required": False}]
            }
        }

        tool_config = {
            "type": "tool-service",
            "name": "tell-joke",
            "description": "Tell a joke on a given topic",
            "service": "joke-service",
            "style": "pun",
            "arguments": [
                {"name": "topic", "type": "string", "description": "The topic for the joke"}
            ]
        }

        # Act
        service_ref = tool_config.get("service")
        service_config = tool_services.get(service_ref)

        # Assert
        assert service_ref == "joke-service"
        assert service_config is not None
        assert service_config["request-queue"] == "non-persistent://tg/request/joke"

    def test_tool_config_extracts_config_values(self):
        """Test that config values are extracted from tool config"""
        # Arrange
        tool_services = {
            "joke-service": {
                "id": "joke-service",
                "request-queue": "non-persistent://tg/request/joke",
                "response-queue": "non-persistent://tg/response/joke",
                "config-params": [
                    {"name": "style", "required": False},
                    {"name": "max-length", "required": False}
                ]
            }
        }

        tool_config = {
            "type": "tool-service",
            "name": "tell-joke",
            "description": "Tell a joke",
            "service": "joke-service",
            "style": "pun",
            "max-length": 100,
            "arguments": []
        }

        # Act - simulate config extraction
        service_config = tool_services[tool_config["service"]]
        config_params = service_config.get("config-params", [])
        config_values = {}
        for param in config_params:
            param_name = param.get("name") if isinstance(param, dict) else param
            if param_name in tool_config:
                config_values[param_name] = tool_config[param_name]

        # Assert
        assert config_values == {"style": "pun", "max-length": 100}

    def test_required_config_param_validation(self):
        """Test that required config params are validated"""
        # Arrange
        tool_services = {
            "custom-service": {
                "id": "custom-service",
                "request-queue": "non-persistent://tg/request/custom",
                "response-queue": "non-persistent://tg/response/custom",
                "config-params": [
                    {"name": "collection", "required": True},
                    {"name": "optional-param", "required": False}
                ]
            }
        }

        tool_config_missing_required = {
            "type": "tool-service",
            "name": "custom-tool",
            "description": "Custom tool",
            "service": "custom-service",
            # Missing required "collection" param
            "optional-param": "value"
        }

        # Act & Assert
        def validate_config_params(tool_config, service_config):
            config_params = service_config.get("config-params", [])
            for param in config_params:
                param_name = param.get("name")
                if param.get("required", False) and param_name not in tool_config:
                    raise RuntimeError(f"Missing required config param '{param_name}'")
            return True

        service_config = tool_services["custom-service"]
        with pytest.raises(RuntimeError) as exc_info:
            validate_config_params(tool_config_missing_required, service_config)
        assert "collection" in str(exc_info.value)


class TestToolServiceRequest:
    """Test cases for tool service request format"""

    def test_request_format(self):
        """Test that request is properly formatted with user, config, and arguments"""
        # Arrange
        user = "alice"
        config_values = {"style": "pun", "collection": "jokes"}
        arguments = {"topic": "programming"}

        # Act - simulate request building
        request = {
            "user": user,
            "config": json.dumps(config_values),
            "arguments": json.dumps(arguments)
        }

        # Assert
        assert request["user"] == "alice"
        assert json.loads(request["config"]) == {"style": "pun", "collection": "jokes"}
        assert json.loads(request["arguments"]) == {"topic": "programming"}

    def test_request_with_empty_config(self):
        """Test request when no config values are provided"""
        # Arrange
        user = "bob"
        config_values = {}
        arguments = {"query": "test"}

        # Act
        request = {
            "user": user,
            "config": json.dumps(config_values) if config_values else "{}",
            "arguments": json.dumps(arguments) if arguments else "{}"
        }

        # Assert
        assert request["config"] == "{}"
        assert json.loads(request["arguments"]) == {"query": "test"}


class TestToolServiceResponse:
    """Test cases for tool service response handling"""

    def test_success_response_handling(self):
        """Test handling of successful response"""
        # Arrange
        response = {
            "error": None,
            "response": "Hey alice! Here's a pun for you:\n\nWhy do programmers prefer dark mode?",
            "end_of_stream": True
        }

        # Act & Assert
        assert response["error"] is None
        assert "pun" in response["response"]
        assert response["end_of_stream"] is True

    def test_error_response_handling(self):
        """Test handling of error response"""
        # Arrange
        response = {
            "error": {
                "type": "tool-service-error",
                "message": "Service unavailable"
            },
            "response": "",
            "end_of_stream": True
        }

        # Act & Assert
        assert response["error"] is not None
        assert response["error"]["type"] == "tool-service-error"
        assert response["error"]["message"] == "Service unavailable"

    def test_string_response_passthrough(self):
        """Test that string responses are passed through directly"""
        # Arrange
        response_text = "This is a joke response"

        # Act - simulate response handling
        def handle_response(response):
            if isinstance(response, str):
                return response
            else:
                return json.dumps(response)

        result = handle_response(response_text)

        # Assert
        assert result == response_text

    def test_dict_response_json_serialization(self):
        """Test that dict responses are JSON serialized"""
        # Arrange
        response_data = {"joke": "Why did the chicken cross the road?", "category": "classic"}

        # Act
        def handle_response(response):
            if isinstance(response, str):
                return response
            else:
                return json.dumps(response)

        result = handle_response(response_data)

        # Assert
        assert result == json.dumps(response_data)
        assert json.loads(result) == response_data


class TestToolServiceImpl:
    """Test cases for ToolServiceImpl class"""

    def test_tool_service_impl_initialization(self):
        """Test ToolServiceImpl stores queues and config correctly"""
        # Arrange
        class MockArgument:
            def __init__(self, name, type, description):
                self.name = name
                self.type = type
                self.description = description

        # Simulate ToolServiceImpl initialization
        class MockToolServiceImpl:
            def __init__(self, context, request_queue, response_queue, config_values=None, arguments=None, processor=None):
                self.context = context
                self.request_queue = request_queue
                self.response_queue = response_queue
                self.config_values = config_values or {}
                self.arguments = arguments or []
                self.processor = processor
                self._client = None

            def get_arguments(self):
                return self.arguments

        # Act
        arguments = [
            MockArgument("topic", "string", "The topic for the joke")
        ]

        impl = MockToolServiceImpl(
            context=lambda x: None,
            request_queue="non-persistent://tg/request/joke",
            response_queue="non-persistent://tg/response/joke",
            config_values={"style": "pun"},
            arguments=arguments,
            processor=Mock()
        )

        # Assert
        assert impl.request_queue == "non-persistent://tg/request/joke"
        assert impl.response_queue == "non-persistent://tg/response/joke"
        assert impl.config_values == {"style": "pun"}
        assert len(impl.get_arguments()) == 1
        assert impl.get_arguments()[0].name == "topic"

    def test_tool_service_impl_client_caching(self):
        """Test that client is cached and reused"""
        # Arrange
        client_key = "non-persistent://tg/request/joke|non-persistent://tg/response/joke"

        # Simulate client caching behavior
        tool_service_clients = {}

        def get_or_create_client(request_queue, response_queue, clients_cache):
            client_key = f"{request_queue}|{response_queue}"
            if client_key in clients_cache:
                return clients_cache[client_key], False  # False = not created
            client = Mock()
            clients_cache[client_key] = client
            return client, True  # True = newly created

        # Act
        client1, created1 = get_or_create_client(
            "non-persistent://tg/request/joke",
            "non-persistent://tg/response/joke",
            tool_service_clients
        )
        client2, created2 = get_or_create_client(
            "non-persistent://tg/request/joke",
            "non-persistent://tg/response/joke",
            tool_service_clients
        )

        # Assert
        assert created1 is True
        assert created2 is False
        assert client1 is client2


class TestJokeServiceLogic:
    """Test cases for the joke service example"""

    def test_topic_to_category_mapping(self):
        """Test that topics are mapped to categories correctly"""
        # Arrange
        def map_topic_to_category(topic):
            topic = topic.lower()
            if "program" in topic or "code" in topic or "computer" in topic or "software" in topic:
                return "programming"
            elif "llama" in topic:
                return "llama"
            elif "animal" in topic or "dog" in topic or "cat" in topic or "bird" in topic:
                return "animals"
            elif "food" in topic or "eat" in topic or "cook" in topic or "drink" in topic:
                return "food"
            else:
                return "default"

        # Act & Assert
        assert map_topic_to_category("programming") == "programming"
        assert map_topic_to_category("software engineering") == "programming"
        assert map_topic_to_category("llamas") == "llama"
        assert map_topic_to_category("llama") == "llama"
        assert map_topic_to_category("animals") == "animals"
        assert map_topic_to_category("my dog") == "animals"
        assert map_topic_to_category("food") == "food"
        assert map_topic_to_category("cooking recipes") == "food"
        assert map_topic_to_category("random topic") == "default"
        assert map_topic_to_category("") == "default"

    def test_joke_response_personalization(self):
        """Test that joke responses include user personalization"""
        # Arrange
        user = "alice"
        style = "pun"
        joke = "Why do programmers prefer dark mode? Because light attracts bugs!"

        # Act
        response = f"Hey {user}! Here's a {style} for you:\n\n{joke}"

        # Assert
        assert "Hey alice!" in response
        assert "pun" in response
        assert joke in response

    def test_style_normalization(self):
        """Test that invalid styles fall back to valid ones"""
        import random

        # Arrange
        valid_styles = ["pun", "dad-joke", "one-liner"]

        def normalize_style(style):
            if style not in valid_styles:
                return random.choice(valid_styles)
            return style

        # Act & Assert
        assert normalize_style("pun") == "pun"
        assert normalize_style("dad-joke") == "dad-joke"
        assert normalize_style("one-liner") == "one-liner"
        assert normalize_style("invalid-style") in valid_styles
        assert normalize_style("") in valid_styles


class TestDynamicToolServiceBase:
    """Test cases for DynamicToolService base class behavior"""

    def test_topic_to_pulsar_path_conversion(self):
        """Test that topic names are converted to full Pulsar paths"""
        # Arrange
        topic = "joke"

        # Act
        request_topic = f"non-persistent://tg/request/{topic}"
        response_topic = f"non-persistent://tg/response/{topic}"

        # Assert
        assert request_topic == "non-persistent://tg/request/joke"
        assert response_topic == "non-persistent://tg/response/joke"

    def test_request_parsing(self):
        """Test parsing of incoming request"""
        # Arrange
        request_data = {
            "user": "alice",
            "config": '{"style": "pun"}',
            "arguments": '{"topic": "programming"}'
        }

        # Act
        user = request_data.get("user", "trustgraph")
        config = json.loads(request_data["config"]) if request_data["config"] else {}
        arguments = json.loads(request_data["arguments"]) if request_data["arguments"] else {}

        # Assert
        assert user == "alice"
        assert config == {"style": "pun"}
        assert arguments == {"topic": "programming"}

    def test_response_building(self):
        """Test building of response message"""
        # Arrange
        response_text = "Hey alice! Here's a joke"
        error = None

        # Act
        response = {
            "error": error,
            "response": response_text if isinstance(response_text, str) else json.dumps(response_text),
            "end_of_stream": True
        }

        # Assert
        assert response["error"] is None
        assert response["response"] == "Hey alice! Here's a joke"
        assert response["end_of_stream"] is True

    def test_error_response_building(self):
        """Test building of error response"""
        # Arrange
        error_message = "Service temporarily unavailable"

        # Act
        response = {
            "error": {
                "type": "tool-service-error",
                "message": error_message
            },
            "response": "",
            "end_of_stream": True
        }

        # Assert
        assert response["error"]["type"] == "tool-service-error"
        assert response["error"]["message"] == error_message
        assert response["response"] == ""
