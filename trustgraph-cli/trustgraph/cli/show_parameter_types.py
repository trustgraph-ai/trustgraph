"""
Shows all defined parameter types used in flow classes.

Parameter types define the schema and constraints for parameters that can
be used in flow class definitions. This includes data types, default values,
valid enums, and validation rules.
"""

import argparse
import asyncio
import os
import tabulate
from trustgraph.api import AsyncSocketClient
import json

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)

def format_enum_values(enum_list):
    """
    Format enum values for display, handling both old and new formats.
    """
    if not enum_list:
        return "Any value"

    enum_items = []
    for item in enum_list:
        if isinstance(item, dict):
            enum_id = item.get("id", "")
            description = item.get("description", "")
            if description:
                enum_items.append(f"{enum_id} ({description})")
            else:
                enum_items.append(enum_id)
        else:
            enum_items.append(str(item))

    return "\n".join(f"• {item}" for item in enum_items)

def format_constraints(param_type_def):
    """
    Format validation constraints for display.
    """
    constraints = []

    if "minimum" in param_type_def:
        constraints.append(f"min: {param_type_def['minimum']}")
    if "maximum" in param_type_def:
        constraints.append(f"max: {param_type_def['maximum']}")
    if "minLength" in param_type_def:
        constraints.append(f"min length: {param_type_def['minLength']}")
    if "maxLength" in param_type_def:
        constraints.append(f"max length: {param_type_def['maxLength']}")
    if "pattern" in param_type_def:
        constraints.append(f"pattern: {param_type_def['pattern']}")
    if param_type_def.get("required", False):
        constraints.append("required")

    return ", ".join(constraints) if constraints else "None"

def format_param_type(param_type_name, param_type_def):
    """Format a single parameter type for display."""
    table = []
    table.append(("name", param_type_name))
    table.append(("description", param_type_def.get("description", "")))
    table.append(("type", param_type_def.get("type", "unknown")))

    default = param_type_def.get("default")
    if default is not None:
        table.append(("default", str(default)))

    enum_list = param_type_def.get("enum")
    if enum_list:
        enum_str = format_enum_values(enum_list)
        table.append(("valid values", enum_str))

    constraints = format_constraints(param_type_def)
    if constraints != "None":
        table.append(("constraints", constraints))

    return table

async def fetch_all_param_types(client):
    """Fetch all parameter types concurrently."""

    # Round 1: list parameter types
    resp = await client._send_request("config", None, {
        "operation": "list",
        "type": "parameter-type",
    })
    param_type_names = resp.get("directory", [])

    if not param_type_names:
        return [], {}

    # Round 2: get all parameter types in parallel
    tasks = [
        client._send_request("config", None, {
            "operation": "get",
            "keys": [{"type": "parameter-type", "key": name}],
        })
        for name in param_type_names
    ]
    results = await asyncio.gather(*tasks)

    param_type_defs = {}
    for name, resp in zip(param_type_names, results):
        values = resp.get("values", [])
        if values:
            try:
                param_type_defs[name] = json.loads(values[0].get("value", "{}"))
            except (json.JSONDecodeError, AttributeError):
                pass

    return param_type_names, param_type_defs

async def fetch_single_param_type(client, param_type_name):
    """Fetch a single parameter type."""
    resp = await client._send_request("config", None, {
        "operation": "get",
        "keys": [{"type": "parameter-type", "key": param_type_name}],
    })
    values = resp.get("values", [])
    if values:
        return json.loads(values[0].get("value", "{}"))
    return None

def show_parameter_types(url, token=None):
    """Show all parameter type definitions."""

    async def _fetch():
        async with AsyncSocketClient(url, timeout=60, token=token) as client:
            return await fetch_all_param_types(client)

    param_type_names, param_type_defs = asyncio.run(_fetch())

    if not param_type_names:
        print("No parameter types defined.")
        return

    for name in param_type_names:
        if name not in param_type_defs:
            print(f"Error retrieving parameter type '{name}'")
            print()
            continue

        table = format_param_type(name, param_type_defs[name])

        print(tabulate.tabulate(
            table,
            tablefmt="pretty",
            stralign="left",
        ))
        print()

def show_specific_parameter_type(url, param_type_name, token=None):
    """Show a specific parameter type definition."""

    async def _fetch():
        async with AsyncSocketClient(url, timeout=60, token=token) as client:
            return await fetch_single_param_type(client, param_type_name)

    param_type_def = asyncio.run(_fetch())

    if param_type_def is None:
        print(f"Error retrieving parameter type '{param_type_name}'")
        return

    table = format_param_type(param_type_name, param_type_def)

    print(tabulate.tabulate(
        table,
        tablefmt="pretty",
        stralign="left",
    ))

def main():
    parser = argparse.ArgumentParser(
        prog='tg-show-parameter-types',
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        '-u', '--api-url',
        default=default_url,
        help=f'API URL (default: {default_url})',
    )

    parser.add_argument(
        '--token',
        default=default_token,
        help='Authentication token (default: $TRUSTGRAPH_TOKEN)',
    )

    parser.add_argument(
        '-t', '--type',
        help='Show only the specified parameter type',
    )

    args = parser.parse_args()

    try:
        if args.type:
            show_specific_parameter_type(args.api_url, args.type, args.token)
        else:
            show_parameter_types(args.api_url, args.token)

    except Exception as e:
        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()
