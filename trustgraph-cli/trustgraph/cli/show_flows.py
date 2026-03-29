"""
Shows configured flows.
"""

import argparse
import asyncio
import os
import tabulate
from trustgraph.api import Api, AsyncSocketClient
import json

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)

def describe_interfaces(intdefs, flow):

    intfs = flow.get("interfaces", {})

    lst = []

    for k, v in intdefs.items():

        if intdefs[k].get("visible", False):

            label = intdefs[k].get("description", k)
            kind = intdefs[k].get("kind", None)

            if kind == "request-response":
                req = intfs[k]["request"]
                resp = intfs[k]["response"]

                lst.append(f"{k} request: {req}")
                lst.append(f"{k} response: {resp}")

            if kind == "send":
                q = intfs[k]

                lst.append(f"{k}: {q}")

    return "\n".join(lst)

def get_enum_description(param_value, param_type_def):
    """
    Get the human-readable description for an enum value
    """
    enum_list = param_type_def.get("enum", [])

    for enum_item in enum_list:
        if isinstance(enum_item, dict):
            if enum_item.get("id") == param_value:
                return enum_item.get("description", param_value)
        elif enum_item == param_value:
            return param_value

    return param_value

def format_parameters(flow_params, blueprint_params_metadata, param_type_defs):
    """
    Format flow parameters with their human-readable descriptions.

    param_type_defs is a dict of type_name -> parsed type definition,
    pre-fetched concurrently.
    """
    if not flow_params:
        return "None"

    param_list = []

    sorted_params = sorted(
        blueprint_params_metadata.items(),
        key=lambda x: x[1].get("order", 999)
    )

    for param_name, param_meta in sorted_params:
        if param_name in flow_params:
            value = flow_params[param_name]
            description = param_meta.get("description", param_name)
            param_type = param_meta.get("type", "")
            controlled_by = param_meta.get("controlled-by", None)

            display_value = value
            if param_type and param_type in param_type_defs:
                display_value = get_enum_description(
                    value, param_type_defs[param_type]
                )

            line = f"• {description}: {display_value}"

            if controlled_by:
                line += f" (controlled by {controlled_by})"

            param_list.append(line)

    for param_name, value in flow_params.items():
        if param_name not in blueprint_params_metadata:
            param_list.append(f"• {param_name}: {value} (undefined)")

    return "\n".join(param_list) if param_list else "None"

async def fetch_show_flows(client):
    """Fetch all data needed for show_flows concurrently."""

    # Round 1: list interfaces and list flows in parallel
    interface_names_resp, flow_ids_resp = await asyncio.gather(
        client._send_request("config", None, {
            "operation": "list",
            "type": "interface-description",
        }),
        client._send_request("flow", None, {
            "operation": "list-flows",
        }),
    )

    interface_names = interface_names_resp.get("directory", [])
    flow_ids = flow_ids_resp.get("flow-ids", [])

    if not flow_ids:
        return {}, [], {}, {}

    # Round 2: get all interfaces + all flows in parallel
    interface_tasks = [
        client._send_request("config", None, {
            "operation": "get",
            "keys": [{"type": "interface-description", "key": name}],
        })
        for name in interface_names
    ]

    flow_tasks = [
        client._send_request("flow", None, {
            "operation": "get-flow",
            "flow-id": fid,
        })
        for fid in flow_ids
    ]

    results = await asyncio.gather(*interface_tasks, *flow_tasks)

    # Split results
    interface_results = results[:len(interface_names)]
    flow_results = results[len(interface_names):]

    # Parse interfaces
    interface_defs = {}
    for name, resp in zip(interface_names, interface_results):
        values = resp.get("values", [])
        if values:
            interface_defs[name] = json.loads(values[0].get("value", "{}"))

    # Parse flows
    flows = {}
    for fid, resp in zip(flow_ids, flow_results):
        flow_data = resp.get("flow", "{}")
        flows[fid] = json.loads(flow_data) if isinstance(flow_data, str) else flow_data

    # Round 3: get all blueprints in parallel
    blueprint_names = set()
    for flow in flows.values():
        bp = flow.get("blueprint-name", "")
        if bp:
            blueprint_names.add(bp)

    blueprint_tasks = [
        client._send_request("flow", None, {
            "operation": "get-blueprint",
            "blueprint-name": bp_name,
        })
        for bp_name in blueprint_names
    ]

    blueprint_results = await asyncio.gather(*blueprint_tasks)

    blueprints = {}
    for bp_name, resp in zip(blueprint_names, blueprint_results):
        bp_data = resp.get("blueprint-definition", "{}")
        blueprints[bp_name] = json.loads(bp_data) if isinstance(bp_data, str) else bp_data

    # Round 4: get all parameter type definitions in parallel
    param_types_needed = set()
    for bp in blueprints.values():
        for param_meta in bp.get("parameters", {}).values():
            pt = param_meta.get("type", "")
            if pt:
                param_types_needed.add(pt)

    param_type_tasks = [
        client._send_request("config", None, {
            "operation": "get",
            "keys": [{"type": "parameter-type", "key": pt}],
        })
        for pt in param_types_needed
    ]

    param_type_results = await asyncio.gather(*param_type_tasks)

    param_type_defs = {}
    for pt, resp in zip(param_types_needed, param_type_results):
        values = resp.get("values", [])
        if values:
            try:
                param_type_defs[pt] = json.loads(values[0].get("value", "{}"))
            except (json.JSONDecodeError, AttributeError):
                pass

    return interface_defs, flow_ids, flows, blueprints, param_type_defs

async def _show_flows_async(url, token=None):

    async with AsyncSocketClient(url, timeout=60, token=token) as client:
        return await fetch_show_flows(client)

def show_flows(url, token=None):

    result = asyncio.run(_show_flows_async(url, token=token))

    interface_defs, flow_ids, flows, blueprints, param_type_defs = result

    if not flow_ids:
        print("No flows.")
        return

    for fid in flow_ids:

        flow = flows[fid]

        table = []
        table.append(("id", fid))
        table.append(("blueprint", flow.get("blueprint-name", "")))
        table.append(("desc", flow.get("description", "")))

        parameters = flow.get("parameters", {})
        if parameters:
            blueprint_name = flow.get("blueprint-name", "")
            if blueprint_name and blueprint_name in blueprints:
                blueprint_params_metadata = blueprints[blueprint_name].get("parameters", {})
                param_str = format_parameters(
                    parameters, blueprint_params_metadata, param_type_defs
                )
            else:
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

    parser.add_argument(
        '-t', '--token',
        default=default_token,
        help='Authentication token (default: $TRUSTGRAPH_TOKEN)',
    )

    args = parser.parse_args()

    try:

        show_flows(
            url=args.api_url,
            token=args.token,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()
