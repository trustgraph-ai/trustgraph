"""
Dump out TrustGraph processor states.
"""

import os
import requests
import argparse

default_metrics_url = "http://localhost:8088/api/metrics"
DEFAULT_TOKEN = os.getenv("TRUSTGRAPH_TOKEN", None)

def dump_status(metrics_url, token=None):

    url = f"{metrics_url}/query?query=processor_info"

    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    resp = requests.get(url, headers=headers)

    obj = resp.json()

    tbl = [
        [
            m["metric"].get("processor", m["metric"]["job"]),
            "\U0001f49a"
        ]
        for m in obj["data"]["result"]
    ]

    for row in tbl:
        print(f"  {row[0]:30} {row[1]}")

def main():

    parser = argparse.ArgumentParser(
        prog='tg-show-processor-state',
        description=__doc__,
    )

    parser.add_argument(
        '-m', '--metrics-url',
        default=default_metrics_url,
        help=f'Metrics URL (default: {default_metrics_url})',
    )

    parser.add_argument(
        '-t', '--token',
        default=DEFAULT_TOKEN,
        help=f'Bearer token for authentication (default: TRUSTGRAPH_TOKEN env var)',
    )

    args = parser.parse_args()

    try:

        dump_status(args.metrics_url, args.token)

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()