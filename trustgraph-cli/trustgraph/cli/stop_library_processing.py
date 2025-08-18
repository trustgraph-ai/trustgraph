"""
Removes a library document processing record.  This is just a record of
procesing, it doesn't stop in-flight processing at the moment.
"""

import argparse
import os
import tabulate
from trustgraph.api import Api, ConfigKey
import json

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_user = "trustgraph"

def stop_processing(
        url, user, id
):

    api = Api(url).library()

    api.stop_processing(user = user, id = id)

def main():

    parser = argparse.ArgumentParser(
        prog='tg-stop-library-processing',
        description=__doc__,
    )

    parser.add_argument(
        '-u', '--api-url',
        default=default_url,
        help=f'API URL (default: {default_url})',
    )

    parser.add_argument(
        '-U', '--user',
        default=default_user,
        help=f'User ID (default: {default_user})'
    )

    parser.add_argument(
        '--id', '--processing-id',
        required=True,
        help=f'Processing ID',
    )

    args = parser.parse_args()

    try:

        stop_processing(
            url = args.api_url,
            user = args.user,
            id = args.id,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()