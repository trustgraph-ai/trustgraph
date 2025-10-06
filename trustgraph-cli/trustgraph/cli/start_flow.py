"""
Starts a processing flow using a defined flow class.

Parameters can be provided in three ways:
1. As key=value pairs: --param model=gpt-4 --param temp=0.7
2. As JSON string: -p '{"model": "gpt-4", "temp": 0.7}'
3. As JSON file: --parameters-file params.json

Note: All parameter values are stored as strings internally, regardless of their
input format. Numbers and booleans will be converted to string representation.
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

    parser.add_argument(
        '--param',
        action='append',
        help='Flow parameter as key=value pair (can be used multiple times, e.g., --param model=gpt-4 --param temp=0.7)',
    )

    args = parser.parse_args()

    try:
        # Parse parameters from command line arguments
        parameters = None

        if args.parameters_file:
            with open(args.parameters_file, 'r') as f:
                params_data = json.load(f)
                # Convert all values to strings
                parameters = {k: str(v) for k, v in params_data.items()}
        elif args.parameters:
            params_data = json.loads(args.parameters)
            # Convert all values to strings
            parameters = {k: str(v) for k, v in params_data.items()}
        elif args.param:
            # Parse key=value pairs
            parameters = {}
            for param in args.param:
                if '=' not in param:
                    raise ValueError(f"Invalid parameter format: {param}. Expected key=value")

                key, value = param.split('=', 1)
                key = key.strip()
                value = value.strip()

                # All parameter values must be strings for Pulsar
                # Just store everything as a string
                parameters[key] = value

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