"""
Uses the knowledge service to fetch a knowledge core which is saved
to a local file in msgpack format.
"""

import argparse
import os
import msgpack

from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")

def write_triple(f, data):
    msg = (
        "t",
        {
            "m": {
                "i": data["metadata"]["id"],
                "m": data["metadata"]["root"],
                "c": data["metadata"]["collection"],
            },
            "t": data["triples"],
        }
    )
    f.write(msgpack.packb(msg, use_bin_type=True))

def write_ge(f, data):
    msg = (
        "ge",
        {
            "m": {
                "i": data["metadata"]["id"],
                "m": data["metadata"]["root"],
                "c": data["metadata"]["collection"],
            },
            "e": [
                {
                    "e": ent["entity"],
                    "v": ent["vector"],
                }
                for ent in data["entities"]
            ]
        }
    )
    f.write(msgpack.packb(msg, use_bin_type=True))

def fetch(url, workspace, id, output, token=None):

    api = Api(url=url, token=token, workspace=workspace)
    socket = api.socket()

    try:
        ge = 0
        t = 0

        with open(output, "wb") as f:

            for response in socket.get_kg_core(id):

                if "triples" in response:
                    t += 1
                    write_triple(f, response["triples"])

                if "graph-embeddings" in response:
                    ge += 1
                    write_ge(f, response["graph-embeddings"])

        print(f"Got: {t} triple, {ge} GE messages.")

    finally:
        socket.close()

def main():

    parser = argparse.ArgumentParser(
        prog='tg-get-kg-core',
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
        '-o', '--output',
        required=True,
        help=f'Output file'
    )

    parser.add_argument(
        '-t', '--token',
        default=default_token,
        help='Authentication token (default: $TRUSTGRAPH_TOKEN)',
    )

    args = parser.parse_args()

    try:

        fetch(
            url=args.url,
            workspace=args.workspace,
            id=args.id,
            output=args.output,
            token=args.token,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()
