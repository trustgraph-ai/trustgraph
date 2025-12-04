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

def query(url, flow_id, template_id, variables, streaming=True, token=None):

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
            full_response = {"text": "", "object": ""}

            # Stream output
            for chunk in response:
                content = chunk.content
                if content:
                    print(content, end="", flush=True)
                    full_response["text"] += content

                # Check if this is an object response (JSON)
                if hasattr(chunk, 'object') and chunk.object:
                    full_response["object"] = chunk.object

            # Handle final output
            if full_response["text"]:
                # Add final newline after streaming text
                print()
            elif full_response["object"]:
                # Print JSON object (pretty-printed)
                print(json.dumps(json.loads(full_response["object"]), indent=4))

        else:
            # Non-streaming: handle response
            if isinstance(response, str):
                print(response)
            elif isinstance(response, dict):
                if "text" in response:
                    print(response["text"])
                elif "object" in response:
                    print(json.dumps(json.loads(response["object"]), indent=4))

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
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()
