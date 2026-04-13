import asyncio
from unittest.mock import AsyncMock, MagicMock

from trustgraph.base.flow import Flow
from trustgraph.base.parameter_spec import Parameter, ParameterSpec
from trustgraph.base.spec import Spec


def test_parameter_spec_is_a_spec_and_adds_parameter_value():
    spec = ParameterSpec("temperature")
    flow = MagicMock(parameter={})
    processor = MagicMock()

    spec.add(flow, processor, {"temperature": 0.7})

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


def test_flow_initialization_calls_registered_specs():
    spec_one = MagicMock()
    spec_two = MagicMock()
    processor = MagicMock(specifications=[spec_one, spec_two])

    flow = Flow("processor-1", "flow-a", processor, {"answer": 42})

    assert flow.id == "processor-1"
    assert flow.name == "flow-a"
    assert flow.producer == {}
    assert flow.consumer == {}
    assert flow.parameter == {}
    spec_one.add.assert_called_once_with(flow, processor, {"answer": 42})
    spec_two.add.assert_called_once_with(flow, processor, {"answer": 42})


def test_flow_start_and_stop_visit_all_consumers():
    consumer_one = AsyncMock()
    consumer_two = AsyncMock()
    flow = Flow("processor-1", "flow-a", MagicMock(specifications=[]), {})
    flow.consumer = {"one": consumer_one, "two": consumer_two}

    asyncio.run(flow.start())
    asyncio.run(flow.stop())

    consumer_one.start.assert_called_once_with()
    consumer_two.start.assert_called_once_with()
    consumer_one.stop.assert_called_once_with()
    consumer_two.stop.assert_called_once_with()


def test_flow_call_returns_values_in_priority_order():
    flow = Flow("processor-1", "flow-a", MagicMock(specifications=[]), {})
    flow.producer["shared"] = "producer-value"
    flow.consumer["consumer-only"] = "consumer-value"
    flow.consumer["shared"] = "consumer-value"
    flow.parameter["parameter-only"] = Parameter("parameter-value")
    flow.parameter["shared"] = Parameter("parameter-value")

    assert flow("shared") == "producer-value"
    assert flow("consumer-only") == "consumer-value"
    assert flow("parameter-only") == "parameter-value"
    assert flow("missing") is None
