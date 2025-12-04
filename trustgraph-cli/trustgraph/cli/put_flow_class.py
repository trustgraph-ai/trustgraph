"""
Uploads a flow class definition.  You can take the output of
tg-get-flow-class and load it back in using this utility.
"""

import argparse
import os
from trustgraph.api import Api
import json

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)

def put_flow_class(url, class_name, config, token=None):

    api = Api(url, token=token)

    class_names = api.flow().put_class(class_name, config)

def main():

    parser = argparse.ArgumentParser(
        prog='tg-put-flow-class',
        description=__doc__,
    )

    parser.add_argument(
        '-u', '--api-url',
        default=default_url,
        help=f'API URL (default: {default_url})',
    )

    parser.add_argument(
        '-t', '--token',
        default=default_token,
        help='Authentication token (default: $TRUSTGRAPH_TOKEN)',
    )

    parser.add_argument(
        '-n', '--class-name',
        help=f'Flow class name',
    )

    parser.add_argument(
        '-c', '--config',
        help=f'Initial configuration to load, should be raw JSON',
    )

    args = parser.parse_args()

    try:

        put_flow_class(
            url=args.api_url,
            class_name=args.class_name,
            config=json.loads(args.config),
            token=args.token,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()