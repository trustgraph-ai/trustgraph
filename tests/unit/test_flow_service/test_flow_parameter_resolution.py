"""
Unit tests for FlowConfig.resolve_parameters: user values, type defaults,
and controlled-by inheritance between flow parameters.
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from trustgraph.flow.service.flow import FlowConfig


PARAMETER_TYPES = {
    "llm-model": {"type": "string", "default": "gpt-5.2"},
    "chunk-size": {"type": "integer", "default": 2000},
    "required-setting": {"type": "string", "required": True},
}

BLUEPRINT = {
    "parameters": {
        "llm-model": {"type": "llm-model"},
        "llm-rag-model": {"type": "llm-model", "controlled-by": "llm-model"},
        "chunk-size": {"type": "chunk-size"},
    }
}


def _flow_config(types=PARAMETER_TYPES):
    async def get(workspace, kind, name):
        assert kind == "parameter-type"
        definition = types.get(name)
        return json.dumps(definition) if definition is not None else None

    config = MagicMock()
    config.get = AsyncMock(side_effect=get)
    return FlowConfig(config, MagicMock())


class TestControlledBy:

    async def test_controlled_parameter_inherits_user_value(self):
        flow_config = _flow_config()

        resolved = await flow_config.resolve_parameters(
            "default", BLUEPRINT, {"llm-model": "gpt-6-luna"},
        )

        assert resolved["llm-model"] == "gpt-6-luna"
        assert resolved["llm-rag-model"] == "gpt-6-luna"

    async def test_explicit_value_overrides_controller(self):
        flow_config = _flow_config()

        resolved = await flow_config.resolve_parameters(
            "default", BLUEPRINT,
            {"llm-model": "gpt-6-luna", "llm-rag-model": "gpt-6.1-terra"},
        )

        assert resolved["llm-model"] == "gpt-6-luna"
        assert resolved["llm-rag-model"] == "gpt-6.1-terra"

    async def test_controlled_parameter_inherits_controller_default(self):
        flow_config = _flow_config()

        resolved = await flow_config.resolve_parameters(
            "default", BLUEPRINT, {},
        )

        assert resolved["llm-model"] == "gpt-5.2"
        assert resolved["llm-rag-model"] == "gpt-5.2"

    async def test_falls_back_to_own_default_without_controller_value(self):
        types = dict(PARAMETER_TYPES)
        types["llm-model"] = {"type": "string"}
        types["rag-model"] = {"type": "string", "default": "rag-default"}
        blueprint = {
            "parameters": {
                "llm-model": {"type": "llm-model"},
                "llm-rag-model": {
                    "type": "rag-model", "controlled-by": "llm-model",
                },
            }
        }
        flow_config = _flow_config(types)

        resolved = await flow_config.resolve_parameters(
            "default", blueprint, {},
        )

        assert "llm-model" not in resolved
        assert resolved["llm-rag-model"] == "rag-default"


class TestDefaults:

    async def test_type_default_applied_to_uncontrolled_parameter(self):
        flow_config = _flow_config()

        resolved = await flow_config.resolve_parameters(
            "default", BLUEPRINT, {"llm-model": "gpt-6-luna"},
        )

        assert resolved["chunk-size"] == "2000"

    async def test_required_parameter_without_value_raises(self):
        blueprint = {
            "parameters": {"setting": {"type": "required-setting"}}
        }
        flow_config = _flow_config()

        with pytest.raises(RuntimeError, match="setting"):
            await flow_config.resolve_parameters("default", blueprint, {})

    async def test_extra_user_parameters_are_kept_as_strings(self):
        flow_config = _flow_config()

        resolved = await flow_config.resolve_parameters(
            "default", BLUEPRINT, {"llm-model": "m", "custom": 3},
        )

        assert resolved["custom"] == "3"

    async def test_blueprint_without_parameters_returns_user_values(self):
        flow_config = _flow_config()

        resolved = await flow_config.resolve_parameters(
            "default", {}, {"a": 1},
        )

        assert resolved == {"a": "1"}
