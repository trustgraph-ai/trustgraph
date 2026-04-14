import argparse
import logging
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

from trustgraph.base.logging import add_logging_args, setup_logging


def test_add_logging_args_uses_environment_defaults(monkeypatch):
    monkeypatch.setenv("LOKI_URL", "http://example.test/loki")
    monkeypatch.setenv("LOKI_USERNAME", "user")
    monkeypatch.setenv("LOKI_PASSWORD", "pass")

    parser = argparse.ArgumentParser()
    add_logging_args(parser)

    args = parser.parse_args([])

    assert args.log_level == "INFO"
    assert args.loki_enabled is True
    assert args.loki_url == "http://example.test/loki"
    assert args.loki_username == "user"
    assert args.loki_password == "pass"


def test_add_logging_args_supports_disabling_loki():
    parser = argparse.ArgumentParser()
    add_logging_args(parser)

    args = parser.parse_args(["--no-loki-enabled"])

    assert args.loki_enabled is False


def test_setup_logging_without_loki_configures_console(monkeypatch):
    basic_config = MagicMock()
    logger = MagicMock()

    monkeypatch.setattr(logging, "basicConfig", basic_config)
    monkeypatch.setattr(logging, "getLogger", lambda name=None: logger)

    setup_logging({"log_level": "debug", "loki_enabled": False, "id": "processor-1"})

    kwargs = basic_config.call_args.kwargs
    assert kwargs["level"] == logging.DEBUG
    assert kwargs["force"] is True
    assert "processor-1" in kwargs["format"]
    assert len(kwargs["handlers"]) == 1
    logger.info.assert_called_once_with("Logging configured with level: debug")


def test_setup_logging_with_loki_enables_queue_listener(monkeypatch):
    basic_config = MagicMock()
    root_logger = MagicMock()
    module_logger = MagicMock()
    urllib3_logger = MagicMock()
    connectionpool_logger = MagicMock()
    queue_handler = MagicMock()
    queue_listener = MagicMock()
    loki_handler = MagicMock()

    logger_map = {
        None: root_logger,
        "trustgraph.base.logging": module_logger,
        "urllib3": urllib3_logger,
        "urllib3.connectionpool": connectionpool_logger,
    }

    monkeypatch.setattr(logging, "basicConfig", basic_config)
    monkeypatch.setattr(logging, "getLogger", lambda name=None: logger_map[name])
    monkeypatch.setattr(
        logging.handlers,
        "QueueHandler",
        MagicMock(return_value=queue_handler),
    )
    monkeypatch.setattr(
        logging.handlers,
        "QueueListener",
        MagicMock(return_value=queue_listener),
    )
    monkeypatch.setitem(
        sys.modules,
        "logging_loki",
        SimpleNamespace(LokiHandler=MagicMock(return_value=loki_handler)),
    )

    setup_logging(
        {
            "log_level": "INFO",
            "loki_enabled": True,
            "loki_url": "http://loki.test/push",
            "loki_username": "user",
            "loki_password": "pass",
            "id": "processor-1",
        }
    )

    assert root_logger.loki_queue_listener is queue_listener
    queue_listener.start.assert_called_once_with()
    urllib3_logger.setLevel.assert_called_once_with(logging.WARNING)
    connectionpool_logger.setLevel.assert_called_once_with(logging.WARNING)
    module_logger.info.assert_any_call("Logging configured with level: INFO")
    module_logger.info.assert_any_call("Loki logging enabled: http://loki.test/push")


def test_setup_logging_falls_back_when_loki_module_missing(monkeypatch, capsys):
    basic_config = MagicMock()
    logger = MagicMock()

    monkeypatch.setattr(logging, "basicConfig", basic_config)
    monkeypatch.setattr(logging, "getLogger", lambda name=None: logger)
    monkeypatch.delitem(sys.modules, "logging_loki", raising=False)
    real_import = __import__

    def fake_import(name, *args, **kwargs):
        if name == "logging_loki":
            raise ImportError("missing")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)

    setup_logging({"log_level": "INFO", "loki_enabled": True, "id": "processor-1"})

    output = capsys.readouterr().out
    assert "python-logging-loki not installed" in output
    logger.warning.assert_called_once_with("Loki logging requested but not available")
