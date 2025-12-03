"""
Uses the DocumentRAG service to answer a question
"""

import argparse
import os
import asyncio
import json
import uuid
from websockets.asyncio.client import connect
from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_user = 'trustgraph'
default_collection = 'default'
default_doc_limit = 10

async def question_streaming(url, flow_id, question, user, collection, doc_limit):
    """Streaming version using websockets"""

    # Convert http:// to ws://
    if url.startswith('http://'):
        url = 'ws://' + url[7:]
    elif url.startswith('https://'):
        url = 'wss://' + url[8:]

    if not url.endswith("/"):
        url += "/"

    url = url + "api/v1/socket"

    mid = str(uuid.uuid4())

    async with connect(url) as ws:
        req = {
            "id": mid,
            "service": "document-rag",
            "flow": flow_id,
            "request": {
                "query": question,
                "user": user,
                "collection": collection,
                "doc-limit": doc_limit,
                "streaming": True
            }
        }

        req = json.dumps(req)
        await ws.send(req)

        while True:
            msg = await ws.recv()
            obj = json.loads(msg)

            if "error" in obj:
                raise RuntimeError(obj["error"])

            if obj["id"] != mid:
                print("Ignore message")
                continue

            response = obj["response"]

            # Handle streaming format (chunk)
            if "chunk" in response:
                chunk = response["chunk"]
                print(chunk, end="", flush=True)
            elif "response" in response:
                # Final response with complete text
                # Already printed via chunks, just add newline
                pass

            if obj["complete"]:
                print()  # Final newline
                break

        await ws.close()

def question_non_streaming(url, flow_id, question, user, collection, doc_limit):
    """Non-streaming version using HTTP API"""

    api = Api(url).flow().id(flow_id)

    resp = api.document_rag(
        question=question, user=user, collection=collection,
        doc_limit=doc_limit,
    )

    print(resp)

def main():

    parser = argparse.ArgumentParser(
        prog='tg-invoke-document-rag',
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
        '-q', '--question',
        required=True,
        help=f'Question to answer',
    )

    parser.add_argument(
        '-U', '--user',
        default=default_user,
        help=f'User ID (default: {default_user})'
    )

    parser.add_argument(
        '-C', '--collection',
        default=default_collection,
        help=f'Collection ID (default: {default_collection})'
    )

    parser.add_argument(
        '-d', '--doc-limit',
        default=default_doc_limit,
        help=f'Document limit (default: {default_doc_limit})'
    )

    parser.add_argument(
        '--no-streaming',
        action='store_true',
        help='Disable streaming (use non-streaming mode)'
    )

    args = parser.parse_args()

    try:

        if not args.no_streaming:
            asyncio.run(
                question_streaming(
                    url=args.url,
                    flow_id=args.flow_id,
                    question=args.question,
                    user=args.user,
                    collection=args.collection,
                    doc_limit=args.doc_limit,
                )
            )
        else:
            question_non_streaming(
                url=args.url,
                flow_id=args.flow_id,
                question=args.question,
                user=args.user,
                collection=args.collection,
                doc_limit=args.doc_limit,
            )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()