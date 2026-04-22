"""
Shows all defined flow blueprints.
"""

import argparse
import asyncio
import os
import tabulate
from trustgraph.api import AsyncSocketClient
import json

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")

def format_parameters(params_metadata, param_type_defs):
    """
    Format parameter metadata for display.

    param_type_defs is a dict of type_name -> parsed type definition,
    pre-fetched concurrently.
    """
    if not params_metadata:
        return "None"

    param_list = []

    sorted_params = sorted(
        params_metadata.items(),
        key=lambda x: x[1].get("order", 999)
    )

    for param_name, param_meta in sorted_params:
        description = param_meta.get("description", param_name)
        param_type = param_meta.get("type", "unknown")

        type_info = param_type
        if param_type in param_type_defs:
            param_type_def = param_type_defs[param_type]
            default = param_type_def.get("default")
            if default is not None:
                type_info = f"{param_type} (default: {default})"

        param_list.append(f"  {param_name}: {description} [{type_info}]")

    return "\n".join(param_list)

async def fetch_data(client, workspace):
    """Fetch all data needed for show_flow_blueprints concurrently."""

    # Round 1: list blueprints
    resp = await client._send_request("flow", None, {
        "operation": "list-blueprints",
        "workspace": workspace,
    })
    blueprint_names = resp.get("blueprint-names", [])

    if not blueprint_names:
        return [], {}, {}

    # Round 2: get all blueprints in parallel
    blueprint_tasks = [
        client._send_request("flow", None, {
            "operation": "get-blueprint",
            "workspace": workspace,
            "blueprint-name": name,
        })
        for name in blueprint_names
    ]
    blueprint_results = await asyncio.gather(*blueprint_tasks)

    blueprints = {}
    for name, resp in zip(blueprint_names, blueprint_results):
        bp_data = resp.get("blueprint-definition", "{}")
        blueprints[name] = json.loads(bp_data) if isinstance(bp_data, str) else bp_data

    # Round 3: get all parameter type definitions in parallel
    param_types_needed = set()
    for bp in blueprints.values():
        for param_meta in bp.get("parameters", {}).values():
            pt = param_meta.get("type", "")
            if pt:
                param_types_needed.add(pt)

    param_type_defs = {}
    if param_types_needed:
        param_type_tasks = [
            client._send_request("config", None, {
                "operation": "get",
                "workspace": workspace,
                "keys": [{"type": "parameter-type", "key": pt}],
            })
            for pt in param_types_needed
        ]
        param_type_results = await asyncio.gather(*param_type_tasks)

        for pt, resp in zip(param_types_needed, param_type_results):
            values = resp.get("values", [])
            if values:
                try:
                    param_type_defs[pt] = json.loads(values[0].get("value", "{}"))
                except (json.JSONDecodeError, AttributeError):
                    pass

    return blueprint_names, blueprints, param_type_defs

async def _show_flow_blueprints_async(url, token=None, workspace="default"):
    async with AsyncSocketClient(url, timeout=60, token=token) as client:
        return await fetch_data(client, workspace)

def show_flow_blueprints(url, token=None, workspace="default"):

    blueprint_names, blueprints, param_type_defs = asyncio.run(
        _show_flow_blueprints_async(
            url, token=token, workspace=workspace,
        )
    )

    if not blueprint_names:
        print("No flow blueprints.")
        return

    for blueprint_name in blueprint_names:
        cls = blueprints[blueprint_name]

        table = []
        table.append(("name", blueprint_name))
        table.append(("description", cls.get("description", "")))

        tags = cls.get("tags", [])
        if tags:
            table.append(("tags", ", ".join(tags)))

        parameters = cls.get("parameters", {})
        if parameters:
            param_str = format_parameters(parameters, param_type_defs)
            table.append(("parameters", param_str))

        print(tabulate.tabulate(
            table,
            tablefmt="pretty",
            stralign="left",
        ))
        print()

def main():

    parser = argparse.ArgumentParser(
        prog='tg-show-flow-blueprints',
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

    parser.add_argument(
        '-w', '--workspace',
        default=default_workspace,
        help=f'Workspace (default: {default_workspace})',
    )

    args = parser.parse_args()

    try:

        show_flow_blueprints(
            url=args.api_url,
            token=args.token,
            workspace=args.workspace,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()
