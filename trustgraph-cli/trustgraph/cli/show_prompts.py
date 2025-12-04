"""
Dumps out the current prompts
"""

import argparse
import os
from trustgraph.api import Api, ConfigKey
import json
import tabulate
import textwrap

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)

def show_config(url, token=None):

    api = Api(url, token=token).config()

    values = api.get([
        ConfigKey(type="prompt", key="system"),
        ConfigKey(type="prompt", key="template-index")
    ])

    system = json.loads(values[0].value)
    ix = json.loads(values[1].value)

    values = api.get([
        ConfigKey(type="prompt", key=f"template.{v}")
        for v in ix
    ])

    print()

    print("System prompt:")

    print(tabulate.tabulate(
        [["prompt", system]],
        tablefmt="pretty",
        maxcolwidths=[None, 70],
        stralign="left"
    ))

    for n, key in enumerate(ix):

        data = json.loads(values[n].value)

        table = []

        table.append(("prompt", data["prompt"]))

        if "response-type" in data:
            table.append(("response", data["response-type"]))

        if "schema" in data:
            table.append(("schema", data["schema"]))

        print()
        print(key + ":")

        print(tabulate.tabulate(
            table,
            tablefmt="pretty",
            maxcolwidths=[None, 70],
            stralign="left"
        ))
        
    print()

def main():

    parser = argparse.ArgumentParser(
        prog='tg-show-prompts',
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

    args = parser.parse_args()

    try:

        show_config(
            url=args.api_url,
            token=args.token,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()