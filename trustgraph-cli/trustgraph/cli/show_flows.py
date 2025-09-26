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

def format_parameters(flow_params, class_params_metadata):
    """
    Format flow parameters with their human-readable descriptions

    Args:
        flow_params: The actual parameter values used in the flow
        class_params_metadata: The parameter metadata from the flow class definition

    Returns:
        Formatted string of parameters with descriptions
    """
    if not flow_params:
        return "None"

    param_list = []

    # Sort parameters by order if available
    sorted_params = sorted(
        class_params_metadata.items(),
        key=lambda x: x[1].get("order", 999)
    )

    for param_name, param_meta in sorted_params:
        if param_name in flow_params:
            value = flow_params[param_name]
            description = param_meta.get("description", param_name)
            param_type = param_meta.get("type", "")
            advanced = param_meta.get("advanced", False)
            controlled_by = param_meta.get("controlled-by", None)

            # Format the parameter line
            line = f"• {description}: {value}"

            # Add metadata indicators
            indicators = []
            if advanced:
                indicators.append("advanced")
            if controlled_by:
                indicators.append(f"controlled by {controlled_by}")

            if indicators:
                line += f" ({', '.join(indicators)})"

            param_list.append(line)

    # Add any parameters that aren't in the class metadata (shouldn't happen normally)
    for param_name, value in flow_params.items():
        if param_name not in class_params_metadata:
            param_list.append(f"• {param_name}: {value} (undefined)")

    return "\n".join(param_list) if param_list else "None"

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

        # Display parameters with human-readable descriptions
        parameters = flow.get("parameters", {})
        if parameters:
            # Try to get the flow class definition for parameter metadata
            class_name = flow.get("class-name", "")
            if class_name:
                try:
                    flow_class = flow_api.get_class(class_name)
                    class_params_metadata = flow_class.get("parameters", {})
                    param_str = format_parameters(parameters, class_params_metadata)
                except Exception as e:
                    # Fallback to JSON if we can't get the class definition
                    param_str = json.dumps(parameters, indent=2)
            else:
                # No class name, fallback to JSON
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