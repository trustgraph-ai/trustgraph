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
import msgpack

default_url = os.getenv("TRUSTGRAPH_URL", 'ws://localhost:8088/')
default_user = 'trustgraph'

def read_message(unpacked, id, user):
    
    if unpacked[0] == "ge":
        msg = unpacked[1]
        return "ge", {
            "metadata": {
                "id": id,
                "metadata": msg["m"]["m"],
                "user": user,
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
                "user": user,
                "collection": "default",   # Not used by receiver?
            },
            "triples": msg["t"],
        }
    else:
        raise RuntimeError("Unpacked unexpected messsage type", unpacked[0])

async def put(url, user, id, input):

    if not url.endswith("/"):
        url += "/"

    url = url + "api/v1/socket"

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

                kind, msg = read_message(unpacked, id, user)

                mid = str(uuid.uuid4())

                if kind == "ge":

                    ge += 1

                    req = json.dumps({
                        "id": mid,
                        "service": "knowledge",
                        "request": {
                            "operation": "put-kg-core",
                            "user": user,
                            "id": id,
                            "graph-embeddings": msg
                        }
                    })

                elif kind == "t":

                    t += 1

                    req = json.dumps({
                        "id": mid,
                        "service": "knowledge",
                        "request": {
                            "operation": "put-kg-core",
                            "user": user,
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
        '-U', '--user',
        default=default_user,
        help=f'User ID (default: {default_user})'
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

    args = parser.parse_args()

    try:

        asyncio.run(
            put(
                url = args.url,
                user = args.user,
                id = args.id,
                input = args.input,
            )
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()