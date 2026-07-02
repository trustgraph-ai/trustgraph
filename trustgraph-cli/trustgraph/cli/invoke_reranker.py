"""
Invokes the reranker service to score and rank documents by relevance
to one or more queries.
"""

import argparse
import json
import os
from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")

def query(url, flow_id, queries, documents, limit, token=None,
          workspace="default"):

    api = Api(url=url, token=token, workspace=workspace)
    socket = api.socket()
    flow = socket.flow(flow_id)

    try:

        query_objects = [
            {"query_id": str(i), "query_text": q}
            for i, q in enumerate(queries)
        ]

        document_objects = [
            {"document_id": str(i), "document_text": d}
            for i, d in enumerate(documents)
        ]

        result = flow.rerank(
            queries=query_objects,
            documents=document_objects,
            limit=limit,
        )

        if "error" in result and result["error"]:
            err = result["error"]
            print(f"Error: [{err.get('type', '')}] {err.get('message', '')}")
            return

        for r in result.get("results", []):
            doc_idx = int(r["document_id"])
            query_idx = int(r["query_id"])
            print(
                f"  {r['score']:.4f} | "
                f"query: {queries[query_idx]} | "
                f"doc: {documents[doc_idx]}"
            )

    finally:
        socket.close()

def main():

    parser = argparse.ArgumentParser(
        prog='tg-invoke-reranker',
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
        '-w', '--workspace',
        default=default_workspace,
        help=f'Workspace (default: {default_workspace})',
    )

    parser.add_argument(
        '-f', '--flow-id',
        default="default",
        help=f'Flow ID (default: default)'
    )

    parser.add_argument(
        '-l', '--limit',
        type=int,
        default=10,
        help='Maximum number of results (default: 10)',
    )

    parser.add_argument(
        '-q', '--query',
        action='append',
        required=True,
        help='Query text (can be specified multiple times)',
    )

    parser.add_argument(
        'documents',
        nargs='+',
        help='Documents to rerank',
    )

    args = parser.parse_args()

    try:

        query(
            url=args.url,
            flow_id=args.flow_id,
            queries=args.query,
            documents=args.documents,
            limit=args.limit,
            token=args.token,
            workspace=args.workspace,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()
