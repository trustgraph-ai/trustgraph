"""
Select relevant ontology subset for given text. Returns matching
classes, object properties, and datatype properties from the loaded
ontologies.
"""

import argparse
import json
import os
from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8888/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")

def query(url, flow_id, text, top_k=10, similarity_threshold=0.3,
          token=None, workspace="default", as_json=False):

    api = Api(url=url, token=token, workspace=workspace)
    socket = api.socket()
    flow = socket.flow(flow_id)

    try:
        result = flow.ontology_subset(
            text=text,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
        )

        if as_json:
            print(json.dumps(result, indent=2))
            return

        print(f"Ontology: {result.get('ontology-id', 'unknown')}")
        print(f"Namespace: {result.get('namespace', '')}")
        print()

        classes = result.get("classes", {})
        if classes:
            print(f"Classes ({len(classes)}):")
            for class_id, class_def in classes.items():
                print(f"  {class_id}")
            print()

        obj_props = result.get("object-properties", {})
        if obj_props:
            print(f"Object Properties ({len(obj_props)}):")
            for prop_id, prop_def in obj_props.items():
                print(f"  {prop_id}")
            print()

        dt_props = result.get("datatype-properties", {})
        if dt_props:
            print(f"Datatype Properties ({len(dt_props)}):")
            for prop_id, prop_def in dt_props.items():
                print(f"  {prop_id}")

    finally:
        socket.close()

def main():

    parser = argparse.ArgumentParser(
        prog='tg-invoke-ontology-subset',
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
        '-k', '--top-k',
        type=int,
        default=10,
        help='Number of top ontology elements to retrieve (default: 10)',
    )

    parser.add_argument(
        '-s', '--similarity-threshold',
        type=float,
        default=0.3,
        help='Similarity threshold for matching (default: 0.3)',
    )

    parser.add_argument(
        '-j', '--json',
        action='store_true',
        default=False,
        help='Output as JSON',
    )

    parser.add_argument(
        'text',
        help='Text to match against ontology elements',
    )

    args = parser.parse_args()

    try:

        query(
            url=args.url,
            flow_id=args.flow_id,
            text=args.text,
            top_k=args.top_k,
            similarity_threshold=args.similarity_threshold,
            token=args.token,
            workspace=args.workspace,
            as_json=args.json,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()
