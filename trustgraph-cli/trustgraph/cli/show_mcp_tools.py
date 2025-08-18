"""
Displays the current MCP (Model Context Protocol) tool configuration
"""

import argparse
import os
from trustgraph.api import Api, ConfigKey
import json
import tabulate
import textwrap

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')

def show_config(url):

    api = Api(url).config()

    values = api.get_values(type="mcp")

    for n, value in enumerate(values):

        data = json.loads(value.value)

        table = []

        table.append(("id", value.key))
        table.append(("remote-name", data["remote-name"]))
        table.append(("url", data["url"]))

        print()

        print(tabulate.tabulate(
            table,
            tablefmt="pretty",
            maxcolwidths=[None, 70],
            stralign="left"
        ))
        
    print()

def main():

    parser = argparse.ArgumentParser(
        prog='tg-show-mcp-tools',
        description=__doc__,
    )

    parser.add_argument(
        '-u', '--api-url',
        default=default_url,
        help=f'API URL (default: {default_url})',
    )

    args = parser.parse_args()

    try:

        show_config(
            url=args.api_url,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()