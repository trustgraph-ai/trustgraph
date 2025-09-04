"""
Uses the NLP Query service to convert natural language questions to GraphQL queries
"""

import argparse
import os
import json
import sys
from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')

def nlp_query(url, flow_id, question, max_results, output_format='json'):

    api = Api(url).flow().id(flow_id)

    resp = api.nlp_query(
        question=question,
        max_results=max_results
    )

    # Check for errors
    if "error" in resp and resp["error"]:
        print("Error:", resp["error"].get("message", "Unknown error"), file=sys.stderr)
        sys.exit(1)

    # Format output based on requested format
    if output_format == 'json':
        print(json.dumps(resp, indent=2))
    elif output_format == 'graphql':
        # Just print the GraphQL query
        if "graphql_query" in resp:
            print(resp["graphql_query"])
        else:
            print("No GraphQL query generated", file=sys.stderr)
            sys.exit(1)
    elif output_format == 'summary':
        # Print a human-readable summary
        if "graphql_query" in resp:
            print(f"Generated GraphQL Query:")
            print("-" * 40)
            print(resp["graphql_query"])
            print("-" * 40)
            if "detected_schemas" in resp and resp["detected_schemas"]:
                print(f"Detected Schemas: {', '.join(resp['detected_schemas'])}")
            if "confidence" in resp:
                print(f"Confidence: {resp['confidence']:.2%}")
            if "variables" in resp and resp["variables"]:
                print(f"Variables: {json.dumps(resp['variables'], indent=2)}")
        else:
            print("No GraphQL query generated", file=sys.stderr)
            sys.exit(1)

def main():

    parser = argparse.ArgumentParser(
        prog='tg-invoke-nlp-query',
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
        help='Natural language question to convert to GraphQL',
    )

    parser.add_argument(
        '-m', '--max-results',
        type=int,
        default=100,
        help='Maximum number of results (default: 100)'
    )

    parser.add_argument(
        '--format', 
        choices=['json', 'graphql', 'summary'],
        default='summary',
        help='Output format (default: summary)'
    )

    args = parser.parse_args()

    try:

        nlp_query(
            url=args.url,
            flow_id=args.flow_id,
            question=args.question,
            max_results=args.max_results,
            output_format=args.format,
        )

    except Exception as e:

        print("Exception:", e, flush=True, file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()