"""
Unit tests for AgentStep arguments type conversion

Tests the fix for converting agent tool arguments to strings when creating
AgentStep records, ensuring compatibility with Pulsar schema that requires
Map(String()) for the arguments field.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from trustgraph.schema import AgentStep
from trustgraph.agent.react.types import Action


class TestAgentStepArgumentsConversion:
    """Test cases for AgentStep arguments string conversion"""

    def test_agent_step_with_integer_arguments(self):
        """Test that integer arguments are converted to strings"""
        # Arrange
        action = Action(
            thought="Set volume to 10",
            name="set_volume",
            arguments={"volume_level": 10, "device": "speaker"},
            observation="Volume set successfully"
        )

        # Act - simulate the conversion that happens in service.py
        agent_step = AgentStep(
            thought=action.thought,
            action=action.name,
            arguments={k: str(v) for k, v in action.arguments.items()},
            observation=action.observation
        )

        # Assert
        assert agent_step.arguments["volume_level"] == "10"
        assert isinstance(agent_step.arguments["volume_level"], str)
        assert agent_step.arguments["device"] == "speaker"
        assert isinstance(agent_step.arguments["device"], str)

    def test_agent_step_with_float_arguments(self):
        """Test that float arguments are converted to strings"""
        # Arrange
        action = Action(
            thought="Set temperature",
            name="set_temperature",
            arguments={"temperature": 23.5, "unit": "celsius"},
            observation="Temperature set"
        )

        # Act
        agent_step = AgentStep(
            thought=action.thought,
            action=action.name,
            arguments={k: str(v) for k, v in action.arguments.items()},
            observation=action.observation
        )

        # Assert
        assert agent_step.arguments["temperature"] == "23.5"
        assert isinstance(agent_step.arguments["temperature"], str)
        assert agent_step.arguments["unit"] == "celsius"

    def test_agent_step_with_boolean_arguments(self):
        """Test that boolean arguments are converted to strings"""
        # Arrange
        action = Action(
            thought="Enable feature",
            name="toggle_feature",
            arguments={"enabled": True, "feature_name": "dark_mode"},
            observation="Feature toggled"
        )

        # Act
        agent_step = AgentStep(
            thought=action.thought,
            action=action.name,
            arguments={k: str(v) for k, v in action.arguments.items()},
            observation=action.observation
        )

        # Assert
        assert agent_step.arguments["enabled"] == "True"
        assert isinstance(agent_step.arguments["enabled"], str)
        assert agent_step.arguments["feature_name"] == "dark_mode"

    def test_agent_step_with_none_arguments(self):
        """Test that None arguments are converted to strings"""
        # Arrange
        action = Action(
            thought="Check status",
            name="get_status",
            arguments={"filter": None, "category": "all"},
            observation="Status retrieved"
        )

        # Act
        agent_step = AgentStep(
            thought=action.thought,
            action=action.name,
            arguments={k: str(v) for k, v in action.arguments.items()},
            observation=action.observation
        )

        # Assert
        assert agent_step.arguments["filter"] == "None"
        assert isinstance(agent_step.arguments["filter"], str)
        assert agent_step.arguments["category"] == "all"

    def test_agent_step_with_mixed_type_arguments(self):
        """Test that mixed type arguments are all converted to strings"""
        # Arrange
        action = Action(
            thought="Configure device",
            name="configure_device",
            arguments={
                "name": "Hifi",
                "volume_level": 10,
                "bass_boost": 1.5,
                "enabled": True,
                "preset": None
            },
            observation="Device configured"
        )

        # Act
        agent_step = AgentStep(
            thought=action.thought,
            action=action.name,
            arguments={k: str(v) for k, v in action.arguments.items()},
            observation=action.observation
        )

        # Assert - all values should be strings
        assert all(isinstance(v, str) for v in agent_step.arguments.values())
        assert agent_step.arguments["name"] == "Hifi"
        assert agent_step.arguments["volume_level"] == "10"
        assert agent_step.arguments["bass_boost"] == "1.5"
        assert agent_step.arguments["enabled"] == "True"
        assert agent_step.arguments["preset"] == "None"

    def test_agent_step_with_string_arguments(self):
        """Test that string arguments remain strings (no double conversion)"""
        # Arrange
        action = Action(
            thought="Search for information",
            name="search",
            arguments={"query": "test query", "limit": "10"},
            observation="Search completed"
        )

        # Act
        agent_step = AgentStep(
            thought=action.thought,
            action=action.name,
            arguments={k: str(v) for k, v in action.arguments.items()},
            observation=action.observation
        )

        # Assert
        assert agent_step.arguments["query"] == "test query"
        assert agent_step.arguments["limit"] == "10"
        assert all(isinstance(v, str) for v in agent_step.arguments.values())

    def test_agent_step_with_empty_arguments(self):
        """Test that empty arguments dict works correctly"""
        # Arrange
        action = Action(
            thought="Perform action",
            name="do_something",
            arguments={},
            observation="Action completed"
        )

        # Act
        agent_step = AgentStep(
            thought=action.thought,
            action=action.name,
            arguments={k: str(v) for k, v in action.arguments.items()},
            observation=action.observation
        )

        # Assert
        assert agent_step.arguments == {}
        assert isinstance(agent_step.arguments, dict)

    def test_agent_step_with_numeric_string_values(self):
        """Test arguments that are already strings containing numbers"""
        # Arrange
        action = Action(
            thought="Process order",
            name="process_order",
            arguments={"order_id": "12345", "quantity": 10},
            observation="Order processed"
        )

        # Act
        agent_step = AgentStep(
            thought=action.thought,
            action=action.name,
            arguments={k: str(v) for k, v in action.arguments.items()},
            observation=action.observation
        )

        # Assert
        assert agent_step.arguments["order_id"] == "12345"
        assert agent_step.arguments["quantity"] == "10"
        assert all(isinstance(v, str) for v in agent_step.arguments.values())

    def test_agent_step_conversion_preserves_keys(self):
        """Test that argument keys are preserved during conversion"""
        # Arrange
        action = Action(
            thought="Test",
            name="test_action",
            arguments={
                "param1": 1,
                "param_two": 2,
                "PARAM_THREE": 3,
                "param-four": 4
            },
            observation="Done"
        )

        # Act
        agent_step = AgentStep(
            thought=action.thought,
            action=action.name,
            arguments={k: str(v) for k, v in action.arguments.items()},
            observation=action.observation
        )

        # Assert - verify all keys are preserved
        assert set(agent_step.arguments.keys()) == {
            "param1", "param_two", "PARAM_THREE", "param-four"
        }
        # Verify values are converted
        assert agent_step.arguments["param1"] == "1"
        assert agent_step.arguments["param_two"] == "2"
        assert agent_step.arguments["PARAM_THREE"] == "3"
        assert agent_step.arguments["param-four"] == "4"

    def test_real_world_home_assistant_example(self):
        """Test with real-world Home Assistant volume control example"""
        # Arrange - this is the exact scenario from the bug report
        action = Action(
            thought='The user wants to set the volume of the Hifi. The `set_device_volume` tool can be used for this purpose. The device name is "Hifi" and the desired volume level is 10.',
            name='set_device_volume',
            arguments={'name': 'Hifi', 'volume_level': 10},
            observation='{"speech": {}, "response_type": "action_done", "data": {"targets": [], "success": [{"name": "Hifi", "type": "entity", "id": "media_player.hifi"}], "failed": []}}'
        )

        # Act - this should not raise TypeError
        agent_step = AgentStep(
            thought=action.thought,
            action=action.name,
            arguments={k: str(v) for k, v in action.arguments.items()},
            observation=action.observation
        )

        # Assert
        assert agent_step.arguments["name"] == "Hifi"
        assert agent_step.arguments["volume_level"] == "10"
        assert isinstance(agent_step.arguments["volume_level"], str)

    def test_multiple_actions_in_history(self):
        """Test converting multiple actions in history (as done in service.py)"""
        # Arrange
        history = [
            Action(
                thought="First action",
                name="action1",
                arguments={"count": 5},
                observation="Done 1"
            ),
            Action(
                thought="Second action",
                name="action2",
                arguments={"enabled": True, "name": "test"},
                observation="Done 2"
            ),
            Action(
                thought="Third action",
                name="action3",
                arguments={"value": 3.14},
                observation="Done 3"
            )
        ]

        # Act - simulate the list comprehension in service.py
        agent_steps = [
            AgentStep(
                thought=h.thought,
                action=h.name,
                arguments={k: str(v) for k, v in h.arguments.items()},
                observation=h.observation
            )
            for h in history
        ]

        # Assert
        assert len(agent_steps) == 3

        # First action
        assert agent_steps[0].arguments["count"] == "5"
        assert isinstance(agent_steps[0].arguments["count"], str)

        # Second action
        assert agent_steps[1].arguments["enabled"] == "True"
        assert agent_steps[1].arguments["name"] == "test"
        assert all(isinstance(v, str) for v in agent_steps[1].arguments.values())

        # Third action
        assert agent_steps[2].arguments["value"] == "3.14"
        assert isinstance(agent_steps[2].arguments["value"], str)

    def test_arguments_with_special_characters(self):
        """Test arguments containing special characters are properly converted"""
        # Arrange
        action = Action(
            thought="Process data",
            name="process",
            arguments={
                "text": "Hello, World!",
                "path": "/home/user/file.txt",
                "pattern": "test-*-pattern",
                "count": 42
            },
            observation="Processed"
        )

        # Act
        agent_step = AgentStep(
            thought=action.thought,
            action=action.name,
            arguments={k: str(v) for k, v in action.arguments.items()},
            observation=action.observation
        )

        # Assert
        assert agent_step.arguments["text"] == "Hello, World!"
        assert agent_step.arguments["path"] == "/home/user/file.txt"
        assert agent_step.arguments["pattern"] == "test-*-pattern"
        assert agent_step.arguments["count"] == "42"
        assert all(isinstance(v, str) for v in agent_step.arguments.values())

    def test_zero_and_negative_numbers(self):
        """Test that zero and negative numbers are converted correctly"""
        # Arrange
        action = Action(
            thought="Test edge cases",
            name="edge_test",
            arguments={
                "zero": 0,
                "negative": -5,
                "negative_float": -3.14,
                "positive": 10
            },
            observation="Done"
        )

        # Act
        agent_step = AgentStep(
            thought=action.thought,
            action=action.name,
            arguments={k: str(v) for k, v in action.arguments.items()},
            observation=action.observation
        )

        # Assert
        assert agent_step.arguments["zero"] == "0"
        assert agent_step.arguments["negative"] == "-5"
        assert agent_step.arguments["negative_float"] == "-3.14"
        assert agent_step.arguments["positive"] == "10"
        assert all(isinstance(v, str) for v in agent_step.arguments.values())
