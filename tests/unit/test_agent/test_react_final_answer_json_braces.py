"""
A JSON Final Answer with braces inside string values must be returned whole
by the batch ReAct parser.
"""

import json
import logging

import pytest
from trustgraph.agent.react.agent_manager import AgentManager
from trustgraph.agent.react.types import Final

logging.disable(logging.CRITICAL)

ANSWERS = [
    {"q": "}"},
    {"q": "{"},
    {"q": "}{", "n": 1},
    {"summary": "use } to close", "items": [1, 2]},
    {"code": "if x { y }", "n": [1, {"k": "}"}]},
    {"q": 'say "}" \\ {', "n": 2},
]


@pytest.mark.parametrize("answer", ANSWERS)
@pytest.mark.parametrize("sep", [" ", "\n"])
def test_json_final_answer_kept_whole(answer, sep):
    text = "Thought: t\nFinal Answer:" + sep + json.dumps(answer, indent=2)
    result = AgentManager(tools={}).parse_react_response(text)
    assert isinstance(result, Final)
    assert json.loads(result.final) == answer
