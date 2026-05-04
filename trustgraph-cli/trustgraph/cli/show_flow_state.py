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
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")

def dump_status(metrics_url, api_url, flow_id, token=None,
                workspace="default"):

    api = Api(api_url, token=token, workspace=workspace).flow()

    flow = api.get(flow_id)
    blueprint_name = flow["blueprint-name"]

    print()
    print(f"Flow {flow_id}")
    show_processors(metrics_url, flow_id, token=token)

    print()
    print(f"Blueprint {blueprint_name}")
    show_processors(metrics_url, blueprint_name, token=token)

    print()

def show_processors(metrics_url, flow_label, token=None):

    url = f"{metrics_url}/query"

    expr = f"consumer_state=\"running\",flow=\"{flow_label}\""

    params = {
        "query": "consumer_state{" + expr + "}"
    }

    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    resp = requests.get(url, params=params, headers=headers)

    obj = resp.json()

    # consumer_state is one sample per consumer (queue); a processor
    # with N subscriptions shows up N times.  Aggregate to one row per
    # processor: green only if every consumer is running.
    by_proc = {}
    for m in obj["data"]["result"]:
        name = m["metric"].get("processor", m["metric"]["job"])
        running = int(m["value"][1]) > 0
        by_proc[name] = by_proc.get(name, True) and running

    for name in sorted(by_proc):
        icon = "\U0001f49a" if by_proc[name] else "\U0000274c"
        print(f"- {name:30} {icon}")

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

    parser.add_argument(
        '-w', '--workspace',
        default=default_workspace,
        help=f'Workspace (default: {default_workspace})',
    )

    args = parser.parse_args()

    try:

        dump_status(
            args.metrics_url, args.api_url, args.flow_id,
            token=args.token, workspace=args.workspace,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()