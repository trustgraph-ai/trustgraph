"""
Puts a knowledge core into the knowledge manager via the API socket.
"""

import argparse
import os
import uuid
import asyncio
import json
from websockets.asyncio.client import connect
import msgpack

default_url = os.getenv("TRUSTGRAPH_URL", 'ws://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")

def read_message(unpacked, id):

    if unpacked[0] == "ge":
        msg = unpacked[1]
        return "ge", {
            "metadata": {
                "id": id,
                "metadata": msg["m"]["m"],
                "collection": "default",  # Not used?
            },
            "entities": [
                {
                    "entity": ent["e"],
                    "vectors": ent["v"],
                }
                for ent in msg["e"]
            ],
        }
    elif unpacked[0] == "t":
        msg = unpacked[1]
        return "t", {
            "metadata": {
                "id": id,
                "metadata": msg["m"]["m"],
                "collection": "default",   # Not used by receiver?
            },
            "triples": msg["t"],
        }
    else:
        raise RuntimeError("Unpacked unexpected messsage type", unpacked[0])

async def put(url, workspace, id, input, token=None):

    if not url.endswith("/"):
        url += "/"

    url = url + "api/v1/socket"

    if token:
        url = f"{url}?token={token}"

    async with connect(url) as ws:

        ge = 0
        t = 0

        with open(input, "rb") as f:

            unpacker = msgpack.Unpacker(f, raw=False)

            while True:

                try:
                    unpacked = unpacker.unpack()
                except:
                    break

                kind, msg = read_message(unpacked, id)

                mid = str(uuid.uuid4())

                if kind == "ge":

                    ge += 1

                    req = json.dumps({
                        "id": mid,
                        "workspace": workspace,
                        "service": "knowledge",
                        "request": {
                            "operation": "put-kg-core",
                            "workspace": workspace,
                            "id": id,
                            "graph-embeddings": msg
                        }
                    })

                elif kind == "t":

                    t += 1

                    req = json.dumps({
                        "id": mid,
                        "workspace": workspace,
                        "service": "knowledge",
                        "request": {
                            "operation": "put-kg-core",
                            "workspace": workspace,
                            "id": id,
                            "triples": msg
                        }
                    })

                else:

                    raise RuntimeError("Unexpected message kind", kind)

                await ws.send(req)

                # Retry loop, wait for right response to come back
                while True:

                    msg = await ws.recv()
                    msg = json.loads(msg)

                    if msg["id"] != mid:
                        continue

                    if "response" in msg:
                        if "error" in msg["response"]:
                            raise RuntimeError(msg["response"]["error"])

                    break

        print(f"Put: {t} triple, {ge} GE messages.")

        await ws.close()

def main():

    parser = argparse.ArgumentParser(
        prog='tg-put-kg-core',
        description=__doc__,
    )

    parser.add_argument(
        '-u', '--url',
        default=default_url,
        help=f'API URL (default: {default_url})',
    )

    parser.add_argument(
        '-w', '--workspace',
        default=default_workspace,
        help=f'Workspace (default: {default_workspace})',
    )

    parser.add_argument(
        '--id', '--identifier',
        required=True,
        help=f'Knowledge core ID',
    )

    parser.add_argument(
        '-i', '--input',
        required=True,
        help=f'Input file'
    )

    parser.add_argument(
        '-t', '--token',
        default=default_token,
        help='Authentication token (default: $TRUSTGRAPH_TOKEN)',
    )

    args = parser.parse_args()

    try:

        asyncio.run(
            put(
                url=args.url,
                workspace=args.workspace,
                id=args.id,
                input=args.input,
                token=args.token,
            )
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()
