"""
Uses the agent service to answer a question
"""

import argparse
import os
import textwrap
import uuid
import asyncio
import json
from websockets.asyncio.client import connect

default_url = os.getenv("TRUSTGRAPH_URL", 'ws://localhost:8088/')
default_user = 'trustgraph'
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

async def question(
        url, question, flow_id, user, collection,
        plan=None, state=None, group=None, verbose=False, streaming=True
):

    if not url.endswith("/"):
        url += "/"

    url = url + "api/v1/socket"

    if verbose:
        output(wrap(question), "\U00002753 ")
        print()

    # Track last chunk type and current outputter for streaming
    last_chunk_type = None
    current_outputter = None

    def think(x):
        if verbose:
            output(wrap(x), "\U0001f914 ")
            print()

    def observe(x):
        if verbose:
            output(wrap(x), "\U0001f4a1 ")
            print()

    mid = str(uuid.uuid4())

    async with connect(url) as ws:

        req = {
            "id": mid,
            "service": "agent",
            "flow": flow_id,
            "request": {
                "question": question,
                "user": user,
                "history": [],
                "streaming": streaming
            }
        }

        # Only add optional fields if they have values
        if state is not None:
            req["request"]["state"] = state
        if group is not None:
            req["request"]["group"] = group

        req = json.dumps(req)

        await ws.send(req)

        while True:

            msg = await ws.recv()

            obj = json.loads(msg)

            if "error" in obj:
                raise RuntimeError(obj["error"])

            if obj["id"] != mid:
                print("Ignore message")
                continue

            response = obj["response"]

            # Handle streaming format (new format with chunk_type)
            if "chunk_type" in response:
                chunk_type = response["chunk_type"]
                content = response.get("content", "")

                # Check if we're switching to a new message type
                if last_chunk_type != chunk_type:
                    # Close previous outputter if exists
                    if current_outputter:
                        current_outputter.__exit__(None, None, None)
                        current_outputter = None
                        print()  # Blank line between message types

                    # Create new outputter for new message type
                    if chunk_type == "thought" and verbose:
                        current_outputter = Outputter(width=78, prefix="\U0001f914  ")
                        current_outputter.__enter__()
                    elif chunk_type == "observation" and verbose:
                        current_outputter = Outputter(width=78, prefix="\U0001f4a1  ")
                        current_outputter.__enter__()
                    # For answer, don't use Outputter - just print as-is

                    last_chunk_type = chunk_type

                # Output the chunk
                if current_outputter:
                    current_outputter.output(content)
                elif chunk_type == "answer":
                    print(content, end="", flush=True)
            else:
                # Handle legacy format (backward compatibility)
                if "thought" in response:
                    think(response["thought"])

                if "observation" in response:
                    observe(response["observation"])

                if "answer" in response:
                    print(response["answer"])

                if "error" in response:
                    raise RuntimeError(response["error"])

            if obj["complete"]:
                # Close any remaining outputter
                if current_outputter:
                    current_outputter.__exit__(None, None, None)
                    current_outputter = None
                # Add final newline if we were outputting answer
                elif last_chunk_type == "answer":
                    print()
                break

        await ws.close()

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
        '-U', '--user',
        default=default_user,
        help=f'User ID (default: {default_user})'
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

    args = parser.parse_args()

    try:

        asyncio.run(
            question(
                url = args.url,
                flow_id = args.flow_id,
                question = args.question,
                user = args.user,
                collection = args.collection,
                plan = args.plan,
                state = args.state,
                group = args.group,
                verbose = args.verbose,
                streaming = not args.no_streaming,
            )
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()
