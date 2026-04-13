"""
Invokes the text completion service by specifying an LLM system prompt
and user prompt.  Both arguments are required.
"""

import argparse
import os
from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)

def query(url, flow_id, system, prompt, streaming=True, token=None,
          show_usage=False):

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
            last_chunk = None
            for chunk in response:
                print(chunk.content, end="", flush=True)
                last_chunk = chunk
            print()

            if show_usage and last_chunk:
                print(
                    f"Input tokens: {last_chunk.in_token}  "
                    f"Output tokens: {last_chunk.out_token}  "
                    f"Model: {last_chunk.model}",
                    file=__import__('sys').stderr,
                )
        else:
            print(response.text)

            if show_usage:
                print(
                    f"Input tokens: {response.in_token}  "
                    f"Output tokens: {response.out_token}  "
                    f"Model: {response.model}",
                    file=__import__('sys').stderr,
                )

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

    parser.add_argument(
        '--show-usage',
        action='store_true',
        help='Show token usage and model on stderr'
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
            show_usage=args.show_usage,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()
