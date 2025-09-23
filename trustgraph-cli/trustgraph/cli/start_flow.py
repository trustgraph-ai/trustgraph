"""
Starts a processing flow using a defined flow class
"""

import argparse
import os
import tabulate
from trustgraph.api import Api
import json

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')

def start_flow(url, class_name, flow_id, description, parameters=None):

    api = Api(url).flow()

    api.start(
        class_name = class_name,
        id = flow_id,
        description = description,
        parameters = parameters,
    )

def main():

    parser = argparse.ArgumentParser(
        prog='tg-start-flow',
        description=__doc__,
    )

    parser.add_argument(
        '-u', '--api-url',
        default=default_url,
        help=f'API URL (default: {default_url})',
    )

    parser.add_argument(
        '-n', '--class-name',
        required=True,
        help=f'Flow class name',
    )

    parser.add_argument(
        '-i', '--flow-id',
        required=True,
        help=f'Flow ID',
    )

    parser.add_argument(
        '-d', '--description',
        required=True,
        help=f'Flow description',
    )

    parser.add_argument(
        '-p', '--parameters',
        help='Flow parameters as JSON string (e.g., \'{"model": "gpt-4", "temp": 0.7}\')',
    )

    parser.add_argument(
        '--parameters-file',
        help='Path to JSON file containing flow parameters',
    )

    args = parser.parse_args()

    try:
        # Parse parameters from command line arguments
        parameters = None

        if args.parameters_file:
            with open(args.parameters_file, 'r') as f:
                parameters = json.load(f)
        elif args.parameters:
            parameters = json.loads(args.parameters)

        start_flow(
            url = args.api_url,
            class_name = args.class_name,
            flow_id = args.flow_id,
            description = args.description,
            parameters = parameters,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()