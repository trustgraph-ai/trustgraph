"""
Dump out a stream of token rates, input, output and total.  This is averaged
across the time since tg-show-token-rate is started.
"""

import requests
import argparse
import json
import time

default_metrics_url = "http://localhost:8088/api/metrics"

class Collate:

    def look(self, data):
        return sum(
            [
                float(x["value"][1])
                for x in data["data"]["result"]
            ]
        )

    def __init__(self, data):
        self.last = self.look(data)
        self.total = 0
        self.time = 0

    def record(self, data, time):

        value = self.look(data)
        delta = value - self.last
        self.last = value

        self.total += delta
        self.time += time

        return delta/time, self.total/self.time

def dump_status(metrics_url, number_samples, period):

    input_url = f"{metrics_url}/query?query=input_tokens_total"
    output_url = f"{metrics_url}/query?query=output_tokens_total"

    resp = requests.get(input_url)
    obj = resp.json()
    input = Collate(obj)

    resp = requests.get(output_url)
    obj = resp.json()
    output = Collate(obj)

    print(f"{'Input':>10s} {'Output':>10s} {'Total':>10s}")
    print(f"{'-----':>10s} {'------':>10s} {'-----':>10s}")

    for i in range(number_samples):

        time.sleep(period)

        resp = requests.get(input_url)
        obj = resp.json()
        inr, inl = input.record(obj, period)

        resp = requests.get(output_url)
        obj = resp.json()
        outr, outl = output.record(obj, period)
        
        print(f"{inl:10.1f} {outl:10.1f} {inl+outl:10.1f}")

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
        '-p', '--period',
        type=int,
        default=1,
        help=f'Metrics period (default: 1)',
    )

    parser.add_argument(
        '-n', '--number-samples',
        type=int,
        default=100,
        help=f'Metrics period (default: 100)',
    )

    args = parser.parse_args()

    try:

        dump_status(**vars(args))

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()