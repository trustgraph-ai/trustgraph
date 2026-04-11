"""
Invokes the LLM prompt service by specifying the prompt template to use
and values for the variables in the prompt template.  The
prompt template is identified by its template identifier e.g.
question, extract-definitions.  Template variable values are specified
using key=value arguments on the command line, and these replace
{{key}} placeholders in the template.
"""

import argparse
import os
import json
from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)

def query(url, flow_id, template_id, variables, streaming=True, token=None,
          show_usage=False):

    # Create API client
    api = Api(url=url, token=token)
    socket = api.socket()
    flow = socket.flow(flow_id)

    try:
        # Call prompt
        response = flow.prompt(
            id=template_id,
            variables=variables,
            streaming=streaming
        )

        if streaming:
            last_chunk = None
            for chunk in response:
                if chunk.content:
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
        prog='tg-invoke-prompt',
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
        '-f', '--flow-id',
        default="default",
        help=f'Flow ID (default: default)'
    )

    parser.add_argument(
        'id',
        metavar='template-id',
        nargs=1,
        help=f'Prompt identifier e.g. question, extract-definitions',
    )

    parser.add_argument(
        'variable',
        nargs='*',
        metavar="variable=value",
        help='''Prompt template terms of the form variable=value, can be
specified multiple times''',
    )

    parser.add_argument(
        '--no-streaming',
        action='store_true',
        help='Disable streaming (default: streaming enabled for text responses)'
    )

    parser.add_argument(
        '--show-usage',
        action='store_true',
        help='Show token usage and model on stderr'
    )

    args = parser.parse_args()

    variables = {}

    for variable in args.variable:

        toks = variable.split("=", 1)
        if len(toks) != 2:
            raise RuntimeError(f"Malformed variable: {variable}")

        variables[toks[0]] = toks[1]

    try:

        query(
            url=args.url,
            flow_id=args.flow_id,
            template_id=args.id[0],
            variables=variables,
            streaming=not args.no_streaming,
            token=args.token,
            show_usage=args.show_usage,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()
