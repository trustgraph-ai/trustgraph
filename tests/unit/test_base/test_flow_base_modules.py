import asyncio
from unittest.mock import AsyncMock, MagicMock

from trustgraph.base.flow import Flow
from trustgraph.base.parameter_spec import Parameter, ParameterSpec
from trustgraph.base.spec import Spec


def test_parameter_spec_is_a_spec_and_adds_parameter_value():
    spec = ParameterSpec("temperature")
    flow = MagicMock(parameter={})
    processor = MagicMock()

    spec.add(flow, processor, {"parameters": {"temperature": 0.7}})

    assert isinstance(spec, Spec)
    assert "temperature" in flow.parameter
    assert isinstance(flow.parameter["temperature"], Parameter)
    assert flow.parameter["temperature"].value == 0.7


def test_parameter_spec_defaults_missing_values_to_none():
    spec = ParameterSpec("model")
    flow = MagicMock(parameter={})

    spec.add(flow, MagicMock(), {})

    assert flow.parameter["model"].value is None


def test_parameter_start_and_stop_are_awaitable():
    parameter = Parameter("value")

    assert asyncio.run(parameter.start()) is None
    assert asyncio.run(parameter.stop()) is None


def test_flow_initialization_sets_attributes():
    processor = MagicMock(specifications=[])

    flow = Flow("processor-1", "flow-a", "default", processor, {"answer": 42})

    assert flow.id == "processor-1"
    assert flow.name == "flow-a"
    assert flow.workspace == "default"
    assert flow.producer == {}
    assert flow.consumer == {}
    assert flow.parameter == {}


def test_flow_start_calls_spec_register():
    spec = AsyncMock()
    spec.register = AsyncMock(return_value=None)
    processor = MagicMock(specifications=[spec])

    flow = Flow("processor-1", "flow-a", "default", processor, {"answer": 42})

    asyncio.run(flow.start())

    spec.register.assert_called_once_with(flow, processor, {"answer": 42})


def test_flow_stop_unregisters_registrations():
    reg = AsyncMock()
    reg.unregister = AsyncMock()

    processor = MagicMock(specifications=[])
    flow = Flow("processor-1", "flow-a", "default", processor, {})
    flow._registrations = [reg]

    asyncio.run(flow.stop())

    reg.unregister.assert_called_once()
    assert flow._registrations == []


def test_flow_call_returns_values_in_priority_order():
    flow = Flow("processor-1", "flow-a", "default", MagicMock(specifications=[]), {})
    flow.producer["shared"] = "producer-value"
    flow.consumer["consumer-only"] = "consumer-value"
    flow.consumer["shared"] = "consumer-value"
    flow.parameter["parameter-only"] = Parameter("parameter-value")
    flow.parameter["shared"] = Parameter("parameter-value")

    assert flow("shared") == "producer-value"
    assert flow("consumer-only") == "consumer-value"
    assert flow("parameter-only") == "parameter-value"
    assert flow("missing") is None
