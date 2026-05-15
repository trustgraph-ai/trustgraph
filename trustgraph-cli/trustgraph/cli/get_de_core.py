"""
Uses the knowledge service to fetch a document embeddings core which is
saved to a local file in msgpack format.
"""

import argparse
import os
import msgpack

from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")

def write_de(f, data):
    msg = (
        "de",
        {
            "m": {
                "i": data["metadata"]["id"],
                "m": data["metadata"]["root"],
                "c": data["metadata"]["collection"],
            },
            "c": [
                {
                    "i": ch["chunk_id"],
                    "v": ch["vector"],
                }
                for ch in data["chunks"]
            ]
        }
    )
    f.write(msgpack.packb(msg, use_bin_type=True))

def fetch(url, workspace, id, output, token=None):

    api = Api(url=url, token=token, workspace=workspace)
    socket = api.socket()

    try:
        de = 0

        with open(output, "wb") as f:

            for response in socket.get_de_core(id):

                if "document-embeddings" in response:
                    de += 1
                    write_de(f, response["document-embeddings"])

        print(f"Got: {de} document embeddings messages.")

    finally:
        socket.close()

def main():

    parser = argparse.ArgumentParser(
        prog='tg-get-de-core',
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
        help=f'Document embeddings core ID',
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
