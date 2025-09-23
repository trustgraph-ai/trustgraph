"""
Shows configured flows.
"""

import argparse
import os
import tabulate
from trustgraph.api import Api, ConfigKey
import json

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')

def get_interface(config_api, i):

    key = ConfigKey("interface-descriptions", i)

    value = config_api.get([key])[0].value

    return json.loads(value)

def describe_interfaces(intdefs, flow):

    intfs = flow.get("interfaces", {})

    lst = []

    for k, v in intdefs.items():

        if intdefs[k].get("visible", False):

            label = intdefs[k].get("description", k)
            kind = intdefs[k].get("kind", None)

            if kind == "request-response":
                req = intfs[k]["request"]
                resp = intfs[k]["request"]

                lst.append(f"{k} request: {req}")
                lst.append(f"{k} response: {resp}")

            if kind == "send":
                q = intfs[k]

                lst.append(f"{k}: {q}")

    return "\n".join(lst)

def show_flows(url):

    api = Api(url)
    config_api = api.config()
    flow_api = api.flow()

    interface_names = config_api.list("interface-descriptions")

    interface_defs = {
        i: get_interface(config_api, i)
        for i in interface_names
    }

    flow_ids = flow_api.list()

    if len(flow_ids) == 0:
        print("No flows.")
        return

    flows = []

    for id in flow_ids:

        flow = flow_api.get(id)

        table = []
        table.append(("id", id))
        table.append(("class", flow.get("class-name", "")))
        table.append(("desc", flow.get("description", "")))

        # Display parameters if they exist
        parameters = flow.get("parameters", {})
        if parameters:
            param_str = json.dumps(parameters, indent=2)
            table.append(("parameters", param_str))

        table.append(("queue", describe_interfaces(interface_defs, flow)))

        print(tabulate.tabulate(
            table,
            tablefmt="pretty",
            stralign="left",
        ))
        print()

def main():

    parser = argparse.ArgumentParser(
        prog='tg-show-flows',
        description=__doc__,
    )

    parser.add_argument(
        '-u', '--api-url',
        default=default_url,
        help=f'API URL (default: {default_url})',
    )

    args = parser.parse_args()

    try:

        show_flows(
            url=args.api_url,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()