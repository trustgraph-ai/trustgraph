"""
Puts a document embeddings core into the knowledge manager via the API
socket.
"""

import argparse
import os
import msgpack

from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")

def read_message(unpacked, id):

    if unpacked[0] == "de":
        msg = unpacked[1]
        return {
            "metadata": {
                "id": id,
                "root": msg["m"]["m"],
                "collection": "default",
            },
            "chunks": [
                {
                    "chunk_id": ch["i"],
                    "vector": ch["v"],
                }
                for ch in msg["c"]
            ],
        }
    else:
        raise RuntimeError("Unexpected message type", unpacked[0])

def put(url, workspace, id, input, token=None):

    api = Api(url=url, token=token, workspace=workspace)
    socket = api.socket()

    try:
        de = 0

        with open(input, "rb") as f:

            unpacker = msgpack.Unpacker(f, raw=False)

            while True:

                try:
                    unpacked = unpacker.unpack()
                except msgpack.OutOfData:
                    break

                msg = read_message(unpacked, id)
                de += 1
                socket.put_de_core(id, document_embeddings=msg)

        print(f"Put: {de} document embeddings messages.")

    finally:
        socket.close()

def main():

    parser = argparse.ArgumentParser(
        prog='tg-put-de-core',
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
