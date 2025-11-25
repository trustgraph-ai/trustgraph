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
import uuid
import asyncio
from websockets.asyncio.client import connect

default_url = os.getenv("TRUSTGRAPH_URL", 'ws://localhost:8088/')

async def query(url, flow_id, template_id, variables, streaming=True):

    if not url.endswith("/"):
        url += "/"

    url = url + "api/v1/socket"

    mid = str(uuid.uuid4())

    async with connect(url) as ws:

        req = {
            "id": mid,
            "service": "prompt",
            "flow": flow_id,
            "request": {
                "id": template_id,
                "variables": variables,
                "streaming": streaming
            }
        }

        await ws.send(json.dumps(req))

        full_response = {"text": "", "object": ""}

        while True:

            msg = await ws.recv()

            obj = json.loads(msg)

            if "error" in obj:
                raise RuntimeError(obj["error"])

            if obj["id"] != mid:
                continue

            response = obj["response"]

            # Handle text responses (streaming)
            if "text" in response and response["text"]:
                if streaming:
                    # Stream output to stdout without newline
                    print(response["text"], end="", flush=True)
                    full_response["text"] += response["text"]
                else:
                    # Non-streaming: print complete response
                    print(response["text"])

            # Handle object responses (JSON, never streamed)
            if "object" in response and response["object"]:
                full_response["object"] = response["object"]

            if obj["complete"]:
                if streaming and full_response["text"]:
                    # Add final newline after streaming text
                    print()
                elif full_response["object"]:
                    # Print JSON object (pretty-printed)
                    print(json.dumps(json.loads(full_response["object"]), indent=4))
                break

        await ws.close()

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

        asyncio.run(query(
            url=args.url,
            flow_id=args.flow_id,
            template_id=args.id[0],
            variables=variables,
            streaming=not args.no_streaming
        ))

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()