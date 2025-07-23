"""
Dumps out token cost configuration
"""

import argparse
import os
from trustgraph.api import Api, ConfigKey
import json
import tabulate
import textwrap

tabulate.PRESERVE_WHITESPACE = True

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')

def show_config(url):

    api = Api(url).config()

    models = api.list("token-costs")

    costs = []

    def fmt(x):
        return "{price:.3f}".format(price = 1000000 * x)

    for model in models:

        try:
            values = json.loads(api.get([
                ConfigKey(type="token-costs", key=model),
            ])[0].value)
            costs.append((
                model,
                fmt(values.get("input_price")),
                fmt(values.get("output_price")),
            ))
        except:
            costs.append((
                model, "-", "-"
            ))

    print(tabulate.tabulate(
        costs,
        tablefmt = "pretty",
        headers = ["model", "input, $/Mt", "output, $/Mt"],
        colalign = ["left", "right", "right"],
#        stralign = ["left", "decimal", "decimal"]
    ))

def main():

    parser = argparse.ArgumentParser(
        prog='tg-show-token-costs',
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