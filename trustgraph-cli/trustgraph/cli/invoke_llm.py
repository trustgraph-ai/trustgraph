"""
Invokes the text completion service by specifying an LLM system prompt
and user prompt.  Both arguments are required.
"""

import argparse
import os
import json
import uuid
import asyncio
from websockets.asyncio.client import connect

default_url = os.getenv("TRUSTGRAPH_URL", 'ws://localhost:8088/')

async def query(url, flow_id, system, prompt, streaming=True):

    if not url.endswith("/"):
        url += "/"

    url = url + "api/v1/socket"

    mid = str(uuid.uuid4())

    async with connect(url) as ws:

        req = {
            "id": mid,
            "service": "text-completion",
            "flow": flow_id,
            "request": {
                "system": system,
                "prompt": prompt,
                "streaming": streaming
            }
        }

        await ws.send(json.dumps(req))

        while True:

            msg = await ws.recv()

            obj = json.loads(msg)

            if "error" in obj:
                raise RuntimeError(obj["error"])

            if obj["id"] != mid:
                continue

            if "response" in obj["response"]:
                if streaming:
                    # Stream output to stdout without newline
                    print(obj["response"]["response"], end="", flush=True)
                else:
                    # Non-streaming: print complete response
                    print(obj["response"]["response"])

            if obj["complete"]:
                if streaming:
                    # Add final newline after streaming
                    print()
                break

        await ws.close()

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

        asyncio.run(query(
            url=args.url,
            flow_id=args.flow_id,
            system=args.system[0],
            prompt=args.prompt[0],
            streaming=not args.no_streaming
        ))

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()