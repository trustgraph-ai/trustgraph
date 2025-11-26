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

    # Track last chunk type and accumulated text for current message
    last_chunk_type = None
    current_message = ""
    need_newline_at_start = False

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
                    # When switching message types, flush accumulated message
                    if current_message:
                        if last_chunk_type == "thought":
                            think(current_message)
                        elif last_chunk_type == "observation":
                            observe(current_message)
                        elif last_chunk_type == "answer":
                            print(current_message)
                            if not current_message.endswith('\n'):
                                print()
                        current_message = ""

                    last_chunk_type = chunk_type

                # Accumulate content for current message type
                current_message += content
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
                # Flush any remaining message
                if current_message:
                    if last_chunk_type == "thought":
                        think(current_message)
                    elif last_chunk_type == "observation":
                        observe(current_message)
                    elif last_chunk_type == "answer":
                        print(current_message)
                        if not current_message.endswith('\n'):
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