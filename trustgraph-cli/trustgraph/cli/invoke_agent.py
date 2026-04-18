"""
Uses the agent service to answer a question
"""

import argparse
import os
import sys
import textwrap
from trustgraph.api import (
    Api,
    ExplainabilityClient,
    ProvenanceEvent,
    Question,
    Analysis,
    Observation,
    Conclusion,
    Decomposition,
    Finding,
    Plan,
    StepResult,
    Synthesis,
    AgentThought,
    AgentObservation,
    AgentAnswer,
)

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")
default_collection = 'default'

class Outputter:
    def __init__(self, width=75, prefix="> "):
        self.width = width
        self.prefix = prefix
        self.column = 0
        self.word_buffer = ""
        self.just_wrapped = False

    def __enter__(self):
        # Print prefix at start of first line
        print(self.prefix, end="", flush=True)
        self.column = len(self.prefix)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Flush remaining word buffer
        if self.word_buffer:
            print(self.word_buffer, end="", flush=True)
            self.column += len(self.word_buffer)
            self.word_buffer = ""

        # Add final newline if not at line start
        if self.column > 0:
            print(flush=True)
            self.column = 0

    def output(self, text):
        for char in text:
            # Handle whitespace (space/tab)
            if char in (' ', '\t'):
                # Flush word buffer if present
                if self.word_buffer:
                    # Check if word + space would exceed width
                    if self.column + len(self.word_buffer) + 1 > self.width:
                        # Wrap: newline + prefix
                        print(flush=True)
                        print(self.prefix, end="", flush=True)
                        self.column = len(self.prefix)
                        self.just_wrapped = True

                    # Output word buffer
                    print(self.word_buffer, end="", flush=True)
                    self.column += len(self.word_buffer)
                    self.word_buffer = ""

                # Output the space
                print(char, end="", flush=True)
                self.column += 1
                self.just_wrapped = False

            # Handle newline
            elif char == '\n':
                if self.just_wrapped:
                    # Skip this newline (already wrapped)
                    self.just_wrapped = False
                else:
                    # Flush word buffer if any
                    if self.word_buffer:
                        print(self.word_buffer, end="", flush=True)
                        self.word_buffer = ""

                    # Output newline + prefix
                    print(flush=True)
                    print(self.prefix, end="", flush=True)
                    self.column = len(self.prefix)
                    self.just_wrapped = False

            # Regular character - add to word buffer
            else:
                self.word_buffer += char
                self.just_wrapped = False

def wrap(text, width=75):
    if text is None: text = "n/a"
    out = textwrap.wrap(
        text, width=width
    )
    return "\n".join(out)

def output(text, prefix="> ", width=78):
    out = textwrap.indent(
        text, prefix=prefix
    )
    print(out)

def question_explainable(
    url, question_text, flow_id, collection,
    state=None, group=None, verbose=False, token=None, debug=False,
    workspace="default",
):
    """Execute agent with explainability - shows provenance events inline."""
    api = Api(url=url, token=token, workspace=workspace)
    socket = api.socket()
    flow = socket.flow(flow_id)
    explain_client = ExplainabilityClient(flow, retry_delay=0.2, max_retries=10)

    try:
        # Track last chunk type for formatting
        last_message_type = None
        current_outputter = None

        # Stream agent with explainability - process events as they arrive
        for item in flow.agent_explain(
            question=question_text,
            collection=collection,
            state=state,
            group=group,
        ):
            if isinstance(item, AgentThought):
                if last_message_type != "thought":
                    if current_outputter:
                        current_outputter.__exit__(None, None, None)
                        current_outputter = None
                        print()  # Blank line between message types
                    if verbose:
                        current_outputter = Outputter(width=78, prefix="\U0001f914  ")
                        current_outputter.__enter__()
                    last_message_type = "thought"
                if current_outputter:
                    current_outputter.output(item.content)
                    if current_outputter.word_buffer:
                        print(current_outputter.word_buffer, end="", flush=True)
                        current_outputter.column += len(current_outputter.word_buffer)
                        current_outputter.word_buffer = ""

            elif isinstance(item, AgentObservation):
                if last_message_type != "observation":
                    if current_outputter:
                        current_outputter.__exit__(None, None, None)
                        current_outputter = None
                        print()
                    if verbose:
                        current_outputter = Outputter(width=78, prefix="\U0001f4a1  ")
                        current_outputter.__enter__()
                    last_message_type = "observation"
                if current_outputter:
                    current_outputter.output(item.content)
                    if current_outputter.word_buffer:
                        print(current_outputter.word_buffer, end="", flush=True)
                        current_outputter.column += len(current_outputter.word_buffer)
                        current_outputter.word_buffer = ""

            elif isinstance(item, AgentAnswer):
                if last_message_type != "answer":
                    if current_outputter:
                        current_outputter.__exit__(None, None, None)
                        current_outputter = None
                        print()
                    last_message_type = "answer"
                # Print answer content directly
                print(item.content, end="", flush=True)

            elif isinstance(item, ProvenanceEvent):
                # Use inline entity if available, otherwise fetch from graph
                prov_id = item.explain_id
                explain_graph = item.explain_graph or "urn:graph:retrieval"

                entity = item.entity
                if entity is None:
                    entity = explain_client.fetch_entity(
                        prov_id,
                        graph=explain_graph,
                        collection=collection
                    )

                if entity is None:
                    if debug:
                        print(f"\n  [warning] Could not fetch entity: {prov_id}", file=sys.stderr)
                    continue

                # Display based on entity type
                if isinstance(entity, Question):
                    print(f"\n  [session] {prov_id}", file=sys.stderr)
                    if entity.query:
                        print(f"    Query: {entity.query}", file=sys.stderr)
                    if entity.timestamp:
                        print(f"    Time: {entity.timestamp}", file=sys.stderr)

                elif isinstance(entity, Analysis):
                    action_label = f": {entity.action}" if entity.action else ""
                    print(f"\n  [analysis{action_label}] {prov_id}", file=sys.stderr)

                elif isinstance(entity, Observation):
                    print(f"\n  [observation] {prov_id}", file=sys.stderr)
                    if entity.document:
                        print(f"    Document: {entity.document}", file=sys.stderr)

                elif isinstance(entity, Decomposition):
                    print(f"\n  [decompose] {prov_id}", file=sys.stderr)
                    for i, goal in enumerate(entity.goals):
                        print(f"    Thread {i}: {goal}", file=sys.stderr)

                elif isinstance(entity, Finding):
                    print(f"\n  [finding] {prov_id}", file=sys.stderr)
                    if entity.goal:
                        print(f"    Goal: {entity.goal}", file=sys.stderr)
                    if entity.document:
                        print(f"    Document: {entity.document}", file=sys.stderr)

                elif isinstance(entity, Plan):
                    print(f"\n  [plan] {prov_id}", file=sys.stderr)
                    for i, step in enumerate(entity.steps):
                        print(f"    Step {i}: {step}", file=sys.stderr)

                elif isinstance(entity, StepResult):
                    print(f"\n  [step-result] {prov_id}", file=sys.stderr)
                    if entity.step:
                        print(f"    Step: {entity.step}", file=sys.stderr)
                    if entity.document:
                        print(f"    Document: {entity.document}", file=sys.stderr)

                elif isinstance(entity, Synthesis):
                    print(f"\n  [synthesis] {prov_id}", file=sys.stderr)
                    if entity.document:
                        print(f"    Document: {entity.document}", file=sys.stderr)

                elif isinstance(entity, Conclusion):
                    print(f"\n  [conclusion] {prov_id}", file=sys.stderr)
                    if entity.document:
                        print(f"    Document: {entity.document}", file=sys.stderr)

                else:
                    if debug:
                        print(f"\n  [unknown] {prov_id} (type: {entity.entity_type})", file=sys.stderr)

        # Close any remaining outputter
        if current_outputter:
            current_outputter.__exit__(None, None, None)
            current_outputter = None

        # Final newline if we ended with answer
        if last_message_type == "answer":
            print()

    finally:
        socket.close()


def question(
        url, question, flow_id, collection,
        plan=None, state=None, group=None, pattern=None,
        verbose=False, streaming=True,
        token=None, explainable=False, debug=False,
        show_usage=False, workspace="default",
):
    # Explainable mode uses the API to capture and process provenance events
    if explainable:
        question_explainable(
            url=url,
            question_text=question,
            flow_id=flow_id,
            collection=collection,
            state=state,
            group=group,
            verbose=verbose,
            token=token,
            debug=debug,
            workspace=workspace,
        )
        return

    if verbose:
        output(wrap(question), "\U00002753 ")
        print()

    # Create API client
    api = Api(url=url, token=token, workspace=workspace)
    socket = api.socket()
    flow = socket.flow(flow_id)

    # Prepare request parameters
    request_params = {
        "question": question,
        "streaming": streaming,
    }

    # Only add optional fields if they have values
    if state is not None:
        request_params["state"] = state
    if group is not None:
        request_params["group"] = group
    if pattern is not None:
        request_params["pattern"] = pattern

    try:
        # Call agent
        response = flow.agent(**request_params)

        # Handle streaming response
        if streaming:
            # Track last chunk type and current outputter for streaming
            last_message_type = None
            current_outputter = None
            last_answer_chunk = None

            for chunk in response:
                message_type = chunk.message_type
                content = chunk.content

                # Check if we're switching to a new message type
                if last_message_type != message_type:
                    # Close previous outputter if exists
                    if current_outputter:
                        current_outputter.__exit__(None, None, None)
                        current_outputter = None
                        print()  # Blank line between message types

                    # Create new outputter for new message type
                    if message_type == "thought" and verbose:
                        current_outputter = Outputter(width=78, prefix="\U0001f914  ")
                        current_outputter.__enter__()
                    elif message_type == "observation" and verbose:
                        current_outputter = Outputter(width=78, prefix="\U0001f4a1  ")
                        current_outputter.__enter__()
                    # For answer, don't use Outputter - just print as-is

                    last_message_type = message_type

                # Output the chunk
                if current_outputter:
                    current_outputter.output(content)
                    # Flush word buffer after each chunk to avoid delay
                    if current_outputter.word_buffer:
                        print(current_outputter.word_buffer, end="", flush=True)
                        current_outputter.column += len(current_outputter.word_buffer)
                        current_outputter.word_buffer = ""
                elif message_type == "final-answer":
                    print(content, end="", flush=True)
                    last_answer_chunk = chunk

            # Close any remaining outputter
            if current_outputter:
                current_outputter.__exit__(None, None, None)
                current_outputter = None
            # Add final newline if we were outputting answer
            elif last_message_type == "final-answer":
                print()

            if show_usage and last_answer_chunk:
                print(
                    f"Input tokens: {last_answer_chunk.in_token}  "
                    f"Output tokens: {last_answer_chunk.out_token}  "
                    f"Model: {last_answer_chunk.model}",
                    file=sys.stderr,
                )

        else:
            # Non-streaming response - but agents use multipart messaging
            # so we iterate through the chunks (which are complete messages, not text chunks)
            for chunk in response:
                # Display thoughts if verbose
                if chunk.message_type == "thought" and verbose:
                    output(wrap(chunk.content), "\U0001f914 ")
                    print()

                # Display observations if verbose
                elif chunk.message_type == "observation" and verbose:
                    output(wrap(chunk.content), "\U0001f4a1 ")
                    print()

                # Display answer
                elif chunk.message_type == "final-answer" or chunk.message_type == "answer":
                    print(chunk.content)

    finally:
        # Clean up socket connection
        socket.close()

def main():

    parser = argparse.ArgumentParser(
        prog='tg-invoke-agent',
        description=__doc__,
    )

    parser.add_argument(
        '-u', '--url',
        default=default_url,
        help=f'API URL (default: {default_url})',
    )

    parser.add_argument(
        '-t', '--token',
        default=default_token,
        help='Authentication token (default: $TRUSTGRAPH_TOKEN)',
    )

    parser.add_argument(
        '-w', '--workspace',
        default=default_workspace,
        help=f'Workspace (default: {default_workspace})',
    )

    parser.add_argument(
        '-f', '--flow-id',
        default="default",
        help=f'Flow ID (default: default)'
    )

    parser.add_argument(
        '-q', '--question',
        required=True,
        help=f'Question to answer',
    )

    parser.add_argument(
        '-C', '--collection',
        default=default_collection,
        help=f'Collection ID (default: {default_collection})'
    )

    parser.add_argument(
        '-l', '--plan',
        help=f'Agent plan (default: unspecified)'
    )

    parser.add_argument(
        '-p', '--pattern',
        choices=['react', 'plan-then-execute', 'supervisor'],
        help='Force execution pattern (default: auto-selected by meta-router)'
    )

    parser.add_argument(
        '-s', '--state',
        help=f'Agent initial state (default: unspecified)'
    )

    parser.add_argument(
        '-g', '--group',
        nargs='+',
        help='Agent tool groups (can specify multiple)'
    )

    parser.add_argument(
        '-v', '--verbose',
        action="store_true",
        help=f'Output thinking/observations'
    )

    parser.add_argument(
        '--no-streaming',
        action="store_true",
        help=f'Disable streaming (use legacy mode)'
    )

    parser.add_argument(
        '-x', '--explainable',
        action='store_true',
        help='Show provenance events: Session, Iterations, Conclusion (implies streaming)'
    )

    parser.add_argument(
        '--debug',
        action='store_true',
        help='Show debug output for troubleshooting'
    )

    parser.add_argument(
        '--show-usage',
        action='store_true',
        help='Show token usage and model on stderr'
    )

    args = parser.parse_args()

    try:

        question(
            url = args.url,
            flow_id = args.flow_id,
            question = args.question,
            collection = args.collection,
            plan = args.plan,
            state = args.state,
            group = args.group,
            pattern = args.pattern,
            verbose = args.verbose,
            streaming = not args.no_streaming,
            token = args.token,
            explainable = args.explainable,
            debug = args.debug,
            show_usage = args.show_usage,
            workspace = args.workspace,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()
