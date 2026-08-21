import pytest
from unittest.mock import Mock, patch

from trustgraph.api import ProtocolException
from trustgraph.cli.show_token_costs import show_config


@patch("trustgraph.cli.show_token_costs.Api")
def test_show_config_handles_invalid_token_cost(mock_api, capsys):
    config_api = Mock()
    mock_api.return_value.config.return_value = config_api

    config_api.list.return_value = ["test-model"]

    result = Mock()
    result.value = "not valid json"
    config_api.get.return_value = [result]

    show_config("http://localhost:8888")

    output = capsys.readouterr().out

    assert "test-model" in output
    assert "-" in output


@patch("trustgraph.cli.show_token_costs.Api")
def test_show_config_does_not_swallow_keyboard_interrupt(mock_api):
    config_api = Mock()
    mock_api.return_value.config.return_value = config_api

    config_api.list.return_value = ["test-model"]
    config_api.get.side_effect = KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        show_config("http://localhost:8888")


@patch("trustgraph.cli.show_token_costs.Api")
def test_show_config_handles_protocol_error(mock_api, capsys):
    config_api = Mock()
    mock_api.return_value.config.return_value = config_api

    config_api.list.return_value = ["test-model"]
    config_api.get.side_effect = ProtocolException("bad response")

    show_config("http://localhost:8888")

    output = capsys.readouterr().out

    assert "test-model" in output
    assert "-" in output
