"""
The streaming ReAct parser must keep the spaces between words of a thought,
wherever the chunk boundaries fall.
"""

import logging

import pytest
from trustgraph.agent.react.streaming_parser import StreamingReActParser

logging.disable(logging.CRITICAL)

THOUGHT = "I need to look up the capital of France before I answer the question."
TEXT = f"Thought: {THOUGHT}\nFinal Answer: Paris."


def _stream(chunks):
    emitted = []
    parser = StreamingReActParser(on_thought_chunk=emitted.append)
    for chunk in chunks:
        parser.feed(chunk)
    parser.finalize()
    return parser.get_result(), "".join(emitted)


@pytest.mark.parametrize("size", [1, 2, 3, 5, 7, 11, 1000])
def test_thought_keeps_spaces_for_any_chunk_size(size):
    chunks = [TEXT[i:i + size] for i in range(0, len(TEXT), size)]
    result, emitted = _stream(chunks)
    assert result.thought == THOUGHT
    assert emitted == THOUGHT


def test_thought_keeps_spaces_with_word_tokens():
    # LLM tokens usually carry the space before a word: "Thought:", " I", " need", ...
    words = TEXT.split(" ")
    chunks = [words[0]] + [" " + w for w in words[1:]]
    result, emitted = _stream(chunks)
    assert result.thought == THOUGHT
    assert emitted == THOUGHT
    assert result.final == "Paris."
