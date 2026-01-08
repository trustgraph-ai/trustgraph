"""
Shows all defined flow classes.
"""

import argparse
import os
import tabulate
from trustgraph.api import Api, ConfigKey
import json

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)

def format_parameters(params_metadata, config_api):
    """
    Format parameter metadata for display

    Args:
        params_metadata: Parameter definitions from flow class
        config_api: API client to get parameter type information

    Returns:
        Formatted string describing parameters
    """
    if not params_metadata:
        return "None"

    param_list = []

    # Sort parameters by order if available
    sorted_params = sorted(
        params_metadata.items(),
        key=lambda x: x[1].get("order", 999)
    )

    for param_name, param_meta in sorted_params:
        description = param_meta.get("description", param_name)
        param_type = param_meta.get("type", "unknown")

        # Get type information if available
        type_info = param_type
        if config_api:
            try:
                key = ConfigKey("parameter-types", param_type)
                type_def_value = config_api.get([key])[0].value
                param_type_def = json.loads(type_def_value)

                # Add default value if available
                default = param_type_def.get("default")
                if default is not None:
                    type_info = f"{param_type} (default: {default})"

            except:
                # If we can't get type definition, just show the type name
                pass

        param_list.append(f"  {param_name}: {description} [{type_info}]")

    return "\n".join(param_list)

def show_flow_classes(url, token=None):

    api = Api(url, token=token)
    flow_api = api.flow()
    config_api = api.config()

    class_names = flow_api.list_classes()

    if len(class_names) == 0:
        print("No flow classes.")
        return

    for class_name in class_names:
        cls = flow_api.get_class(class_name)

        table = []
        table.append(("name", class_name))
        table.append(("description", cls.get("description", "")))

        tags = cls.get("tags", [])
        if tags:
            table.append(("tags", ", ".join(tags)))

        # Show parameters if they exist
        parameters = cls.get("parameters", {})
        if parameters:
            param_str = format_parameters(parameters, config_api)
            table.append(("parameters", param_str))

        print(tabulate.tabulate(
            table,
            tablefmt="pretty",
            stralign="left",
        ))
        print()

def main():

    parser = argparse.ArgumentParser(
        prog='tg-show-flow-classes',
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

        show_flow_classes(
            url=args.api_url,
            token=args.token,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()