"""
Error-handling tests for tg-set-prompt: invalid --schema JSON must become a
clear RuntimeError, and interrupts must not be swallowed (#783).
"""

import json
import sys
from unittest.mock import patch

import pytest

from trustgraph.cli import set_prompt as set_prompt_cli


def _run_main(argv):
    with patch.object(sys, "argv", ["tg-set-prompt", *argv]):
        set_prompt_cli.main()


def test_invalid_schema_json_raises_runtime_error(capsys):
    with patch.object(set_prompt_cli, "set_prompt") as fake_set_prompt:
        # main() catches the RuntimeError and prints it; it must not call the API
        _run_main(["--id", "p1", "--prompt", "hello", "--schema", "{not json"])
        fake_set_prompt.assert_not_called()

    out = capsys.readouterr().out
    assert "JSON schema must be valid JSON" in out


def test_valid_schema_json_is_passed_through():
    with patch.object(set_prompt_cli, "set_prompt") as fake_set_prompt:
        _run_main([
            "--id", "p1", "--prompt", "hello",
            "--schema", json.dumps({"type": "object"}),
        ])

    kwargs = fake_set_prompt.call_args.kwargs
    assert kwargs["schema"] == {"type": "object"}


def test_schema_parse_does_not_swallow_keyboard_interrupt(monkeypatch):
    def interrupt(_text):
        raise KeyboardInterrupt

    monkeypatch.setattr(set_prompt_cli.json, "loads", interrupt)

    with patch.object(set_prompt_cli, "set_prompt"):
        with pytest.raises(KeyboardInterrupt):
            _run_main(["--id", "p1", "--prompt", "hello", "--schema", "{}"])
