"""
Shows configured flows.
"""

import argparse
import os
import tabulate
from trustgraph.api import Api, ConfigKey
import json

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)

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

def get_enum_description(param_value, param_type_def):
    """
    Get the human-readable description for an enum value

    Args:
        param_value: The actual parameter value (e.g., "gpt-4")
        param_type_def: The parameter type definition containing enum objects

    Returns:
        Human-readable description or the original value if not found
    """
    enum_list = param_type_def.get("enum", [])

    # Handle both old format (strings) and new format (objects with id/description)
    for enum_item in enum_list:
        if isinstance(enum_item, dict):
            if enum_item.get("id") == param_value:
                return enum_item.get("description", param_value)
        elif enum_item == param_value:
            return param_value

    # If not found in enum, return original value
    return param_value

def format_parameters(flow_params, blueprint_params_metadata, config_api):
    """
    Format flow parameters with their human-readable descriptions

    Args:
        flow_params: The actual parameter values used in the flow
        blueprint_params_metadata: The parameter metadata from the flow blueprint definition
        config_api: API client to retrieve parameter type definitions

    Returns:
        Formatted string of parameters with descriptions
    """
    if not flow_params:
        return "None"

    param_list = []

    # Sort parameters by order if available
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

            # Try to get enum description if this parameter has a type definition
            display_value = value
            if param_type and config_api:
                try:
                    from trustgraph.api import ConfigKey
                    key = ConfigKey("parameter-type", param_type)
                    type_def_value = config_api.get([key])[0].value
                    param_type_def = json.loads(type_def_value)
                    display_value = get_enum_description(value, param_type_def)
                except:
                    # If we can't get the type definition, just use the original value
                    display_value = value

            # Format the parameter line
            line = f"• {description}: {display_value}"

            # Add controlled-by indicator if present
            if controlled_by:
                line += f" (controlled by {controlled_by})"

            param_list.append(line)

    # Add any parameters that aren't in the blueprint metadata (shouldn't happen normally)
    for param_name, value in flow_params.items():
        if param_name not in blueprint_params_metadata:
            param_list.append(f"• {param_name}: {value} (undefined)")

    return "\n".join(param_list) if param_list else "None"

def show_flows(url, token=None):

    api = Api(url, token=token)
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
        table.append(("blueprint", flow.get("blueprint-name", "")))
        table.append(("desc", flow.get("description", "")))

        # Display parameters with human-readable descriptions
        parameters = flow.get("parameters", {})
        if parameters:
            # Try to get the flow blueprint definition for parameter metadata
            blueprint_name = flow.get("blueprint-name", "")
            if blueprint_name:
                try:
                    flow_blueprint = flow_api.get_blueprint(blueprint_name)
                    blueprint_params_metadata = flow_blueprint.get("parameters", {})
                    param_str = format_parameters(parameters, blueprint_params_metadata, config_api)
                except Exception as e:
                    # Fallback to JSON if we can't get the blueprint definition
                    param_str = json.dumps(parameters, indent=2)
            else:
                # No blueprint name, fallback to JSON
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