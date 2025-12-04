"""
Invokes the text completion service by specifying an LLM system prompt
and user prompt.  Both arguments are required.
"""

import argparse
import os
from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)

def query(url, flow_id, system, prompt, streaming=True, token=None):

    # Create API client
    api = Api(url=url, token=token)
    socket = api.socket()
    flow = socket.flow(flow_id)

    try:
        # Call text completion
        response = flow.text_completion(
            system=system,
            prompt=prompt,
            streaming=streaming
        )

        if streaming:
            # Stream output to stdout without newline
            for chunk in response:
                print(chunk.content, end="", flush=True)
            # Add final newline after streaming
            print()
        else:
            # Non-streaming: print complete response
            print(response)

    finally:
        # Clean up socket connection
        socket.close()

def main():

    parser = argparse.ArgumentParser(
        prog='tg-invoke-llm',
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
        'system',
        nargs=1,
        help='LLM system prompt e.g. You are a helpful assistant',
    )

    parser.add_argument(
        'prompt',
        nargs=1,
        help='LLM prompt e.g. What is 2 + 2?',
    )

    parser.add_argument(
        '-f', '--flow-id',
        default="default",
        help=f'Flow ID (default: default)'
    )

    parser.add_argument(
        '--no-streaming',
        action='store_true',
        help='Disable streaming (default: streaming enabled)'
    )

    args = parser.parse_args()

    try:

        query(
            url=args.url,
            flow_id=args.flow_id,
            system=args.system[0],
            prompt=args.prompt[0],
            streaming=not args.no_streaming,
            token=args.token,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()
