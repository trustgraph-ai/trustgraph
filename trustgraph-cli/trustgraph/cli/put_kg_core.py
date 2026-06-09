"""
Puts a knowledge core into the knowledge manager via the API socket.
"""

import argparse
import os
import msgpack

from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")

def read_message(unpacked, id):

    if unpacked[0] == "ge":
        msg = unpacked[1]
        return "ge", {
            "metadata": {
                "id": id,
                "root": msg["m"]["m"],
                "collection": "default",
            },
            "entities": [
                {
                    "entity": ent["e"],
                    "vector": ent["v"],
                }
                for ent in msg["e"]
            ],
        }
    elif unpacked[0] == "t":
        msg = unpacked[1]
        return "t", {
            "metadata": {
                "id": id,
                "root": msg["m"]["m"],
                "collection": "default",
            },
            "triples": msg["t"],
        }
    elif unpacked[0] == "lm":
        msg = unpacked[1]
        return "lm", {
            "id": msg["i"],
            "kind": msg.get("k", ""),
            "title": msg.get("t", ""),
            "parent-id": msg.get("p", ""),
            "document-type": msg.get("d", ""),
            "comments": msg.get("c", ""),
            "tags": msg.get("g", []),
        }
    elif unpacked[0] == "lb":
        msg = unpacked[1]
        return "lb", {
            "id": msg["i"],
            "data": msg.get("d", b""),
        }
    else:
        raise RuntimeError("Unpacked unexpected messsage type", unpacked[0])

def put(url, workspace, id, input, token=None):

    api = Api(url=url, token=token, workspace=workspace)
    socket = api.socket()

    try:
        ge = 0
        t = 0
        lm = 0
        lb = 0

        with open(input, "rb") as f:

            unpacker = msgpack.Unpacker(f, raw=False)

            while True:

                try:
                    unpacked = unpacker.unpack()
                except msgpack.OutOfData:
                    break

                kind, msg = read_message(unpacked, id)

                if kind == "ge":
                    ge += 1
                    socket.put_kg_core(id, graph_embeddings=msg)

                elif kind == "t":
                    t += 1
                    socket.put_kg_core(id, triples=msg)

                elif kind == "lm":
                    lm += 1
                    socket.put_kg_core(id, library_metadata=msg)

                elif kind == "lb":
                    lb += 1
                    socket.put_kg_core(id, library_blob=msg)

                else:
                    raise RuntimeError("Unexpected message kind", kind)

        print(f"Put: {t} triple, {ge} GE, {lm} library metadata, {lb} library blob messages.")

    finally:
        socket.close()

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

        put(
            url=args.url,
            workspace=args.workspace,
            id=args.id,
            input=args.input,
            token=args.token,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()
