"""
Uses the ObjectsQuery service to execute GraphQL queries against structured data
"""

import argparse
import os
import json
import sys
from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_user = 'trustgraph'
default_collection = 'default'

def objects_query(
        url, flow_id, query, user, collection, variables, operation_name
):

    api = Api(url).flow().id(flow_id)

    # Parse variables if provided as JSON string
    parsed_variables = {}
    if variables:
        try:
            parsed_variables = json.loads(variables)
        except json.JSONDecodeError as e:
            print(f"Error parsing variables JSON: {e}", file=sys.stderr)
            sys.exit(1)

    resp = api.objects_query(
        query=query,
        user=user,
        collection=collection,
        variables=parsed_variables if parsed_variables else None,
        operation_name=operation_name
    )

    # Check for GraphQL errors
    if "errors" in resp and resp["errors"]:
        print("GraphQL Errors:", file=sys.stderr)
        for error in resp["errors"]:
            print(f"  - {error.get('message', 'Unknown error')}", file=sys.stderr)
            if "path" in error and error["path"]:
                print(f"    Path: {error['path']}", file=sys.stderr)
        # Still print data if available
        if "data" in resp and resp["data"]:
            print(json.dumps(resp["data"], indent=2))
        sys.exit(1)

    # Print the data
    if "data" in resp:
        print(json.dumps(resp["data"], indent=2))
    else:
        print("No data returned", file=sys.stderr)
        sys.exit(1)

def main():

    parser = argparse.ArgumentParser(
        prog='tg-invoke-objects-query',
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
        '-q', '--query',
        required=True,
        help='GraphQL query to execute',
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
        '-v', '--variables',
        help='GraphQL variables as JSON string (e.g., \'{"limit": 5}\')'
    )

    parser.add_argument(
        '-o', '--operation-name',
        help='Operation name for multi-operation GraphQL documents'
    )

    args = parser.parse_args()

    try:

        objects_query(
            url=args.url,
            flow_id=args.flow_id,
            query=args.query,
            user=args.user,
            collection=args.collection,
            variables=args.variables,
            operation_name=args.operation_name,
        )

    except Exception as e:

        print("Exception:", e, flush=True, file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()