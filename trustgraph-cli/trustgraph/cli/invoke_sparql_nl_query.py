"""
Answer a natural language question via SPARQL. Chains NL-to-SPARQL
translation with SPARQL execution, returning both the generated query
and its results.
"""

import argparse
import json
import os
from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8888/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")

def query(url, flow_id, question, collection="default", limit=10,
          token=None, workspace="default", as_json=False):

    api = Api(url=url, token=token, workspace=workspace)
    socket = api.socket()
    flow = socket.flow(flow_id)

    try:
        result = flow.sparql_nl_query(
            question=question,
            collection=collection,
            limit=limit,
        )

        if as_json:
            print(json.dumps(result, indent=2))
            return

        entities = result.get("resolved-entities", [])
        if entities:
            print("Resolved entities:")
            for e in entities:
                score = e.get("score", 0)
                print(
                    f"  {e.get('mention', '')} -> {e.get('uri', '')} "
                    f"[{e.get('rdf-type', '')}] (score: {score:.3f})"
                )
            print()

        sparql = result.get("sparql", "")
        if sparql:
            print("Generated SPARQL:")
            print(sparql)
            print()

        query_type = result.get("query-type", "")
        if query_type == "select":
            variables = result.get("variables", [])
            bindings = result.get("bindings", [])
            if variables:
                header = "  ".join(f"?{v:<20}" for v in variables)
                print(header)
                print("-" * len(header))
            for row in bindings:
                print("  ".join(f"{v:<22}" for v in row))
            if not bindings:
                print("No results.")
        elif query_type == "ask":
            print(f"ASK result: {result.get('ask-result', False)}")
        elif query_type:
            print(f"Query type: {query_type}")
        else:
            print("No query results.")

    finally:
        socket.close()

def main():

    parser = argparse.ArgumentParser(
        prog='tg-invoke-sparql-nl-query',
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
        '-c', '--collection',
        default="default",
        help='Collection identifier (default: default)',
    )

    parser.add_argument(
        '-l', '--limit',
        type=int,
        default=10,
        help='Result limit hint for generated query (default: 10)',
    )

    parser.add_argument(
        '-j', '--json',
        action='store_true',
        default=False,
        help='Output as JSON',
    )

    parser.add_argument(
        'question',
        help='Natural language question to answer via SPARQL',
    )

    args = parser.parse_args()

    try:

        query(
            url=args.url,
            flow_id=args.flow_id,
            question=args.question,
            collection=args.collection,
            limit=args.limit,
            token=args.token,
            workspace=args.workspace,
            as_json=args.json,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()
