"""
Braces inside JSON string values must not end the Args block early,
in both the batch and the streaming ReAct parsers.
"""

import json
import logging

import pytest
from trustgraph.agent.react.agent_manager import AgentManager
from trustgraph.agent.react.streaming_parser import StreamingReActParser

logging.disable(logging.CRITICAL)

ARGS = [
    {"q": "}"},
    {"q": "{"},
    {"q": "}{"},
    {"q": "a } b", "n": 1},
    {"code": "if x { y }"},
    {"q": 'say "}" \\ {', "n": [1, {"k": "}"}]},
]


def _text(args, indent, sep):
    return "Thought: t\nAction: tool\nArgs:" + sep + json.dumps(args, indent=indent)


def _stream(text, size):
    parser = StreamingReActParser()
    for i in range(0, len(text), size):
        parser.feed(text[i:i + size])
    parser.finalize()
    return parser.get_result()


@pytest.mark.parametrize("args", ARGS)
@pytest.mark.parametrize("indent", [None, 2])
@pytest.mark.parametrize("sep", [" ", "\n"])
def test_batch_parser(args, indent, sep):
    manager = AgentManager(tools={})
    result = manager.parse_react_response(_text(args, indent, sep))
    assert result.name == "tool"
    assert result.arguments == args


@pytest.mark.parametrize("args", ARGS)
@pytest.mark.parametrize("indent", [None, 2])
@pytest.mark.parametrize("sep", [" ", "\n"])
@pytest.mark.parametrize("size", [1, 7, 1000])
def test_streaming_parser(args, indent, sep, size):
    result = _stream(_text(args, indent, sep), size)
    assert result.name == "tool"
    assert result.arguments == args
