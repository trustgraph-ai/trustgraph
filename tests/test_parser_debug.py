"""
Debug script to understand StreamingReActParser behavior
"""
import sys
sys.path.insert(0, '/home/mark/work/trustgraph.ai/trustgraph/trustgraph-flow')

from trustgraph.agent.react.streaming_parser import StreamingReActParser

# Test the parser with different chunking strategies
full_text = """Thought: I need to search for information about machine learning.
Action: knowledge_query
Args: {
    "question": "What is machine learning?"
}"""

print("=" * 60)
print("TEST 1: Send as single chunk")
print("=" * 60)

parser1 = StreamingReActParser()
parser1.feed(full_text)
parser1.finalize()
result1 = parser1.get_result()
print(f"Result: {result1}")
print(f"Action name: '{result1.name}'")
print(f"Arguments: {result1.arguments}")

print("\n" + "=" * 60)
print("TEST 2: Send line-by-line chunks")
print("=" * 60)

parser2 = StreamingReActParser()
chunks = [
    "Thought: I need to search for information about machine learning.\n",
    "Action: knowledge_query\n",
    "Args: {\n",
    '    "question": "What is machine learning?"\n',
    "}"
]

for i, chunk in enumerate(chunks):
    print(f"\nChunk {i}: {repr(chunk)}")
    print(f"  Before: state={parser2.state}, action_buffer='{parser2.action_buffer}'")
    parser2.feed(chunk)
    print(f"  After:  state={parser2.state}, action_buffer='{parser2.action_buffer}'")

parser2.finalize()
result2 = parser2.get_result()
print(f"\nFinal Result: {result2}")
print(f"Action name: '{result2.name}'")
print(f"Arguments: {result2.arguments}")
