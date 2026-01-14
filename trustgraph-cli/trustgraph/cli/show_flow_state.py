"""
Dump out a flow's processor states
"""

import requests
import argparse
from trustgraph.api import Api
import os

default_metrics_url = "http://localhost:8088/api/metrics"
default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)

def dump_status(metrics_url, api_url, flow_id, token=None):

    api = Api(api_url, token=token).flow()

    flow = api.get(flow_id)
    blueprint_name = flow["blueprint-name"]

    print()
    print(f"Flow {flow_id}")
    show_processors(metrics_url, flow_id)

    print()
    print(f"Blueprint {blueprint_name}")
    show_processors(metrics_url, blueprint_name)

    print()

def show_processors(metrics_url, flow_label):

    url = f"{metrics_url}/query"

    expr = f"consumer_state=\"running\",flow=\"{flow_label}\""

    params = {
        "query": "consumer_state{" + expr + "}"
    }

    resp = requests.get(url, params=params)

    obj = resp.json()

    tbl = [
        [
            m["metric"]["job"],
            "\U0001f49a" if int(m["value"][1]) > 0 else "\U0000274c"
        ]
        for m in obj["data"]["result"]
    ]

    for row in tbl:
        print(f"- {row[0]:30} {row[1]}")

def main():

    parser = argparse.ArgumentParser(
        prog='tg-show-flow-state',
        description=__doc__,
    )

    parser.add_argument(
        '-f', '--flow-id',
        default="default",
        help=f'Flow ID (default: default)'
    )

    parser.add_argument(
        '-u', '--api-url',
        default=default_url,
        help=f'API URL (default: {default_url})',
    )

    parser.add_argument(
        '-m', '--metrics-url',
        default=default_metrics_url,
        help=f'Metrics URL (default: {default_metrics_url})',
    )

    parser.add_argument(
        '-t', '--token',
        default=default_token,
        help='Authentication token (default: $TRUSTGRAPH_TOKEN)',
    )

    args = parser.parse_args()

    try:

        dump_status(args.metrics_url, args.api_url, args.flow_id, token=args.token)

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()