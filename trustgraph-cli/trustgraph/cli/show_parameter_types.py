"""
Shows all defined parameter types used in flow classes.

Parameter types define the schema and constraints for parameters that can
be used in flow class definitions. This includes data types, default values,
valid enums, and validation rules.
"""

import argparse
import os
import tabulate
from trustgraph.api import Api, ConfigKey
import json

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')

def format_enum_values(enum_list):
    """
    Format enum values for display, handling both old and new formats

    Args:
        enum_list: List of enum values (strings or objects with id/description)

    Returns:
        Formatted string describing enum options
    """
    if not enum_list:
        return "Any value"

    enum_items = []
    for item in enum_list:
        if isinstance(item, dict):
            # New format: objects with id and description
            enum_id = item.get("id", "")
            description = item.get("description", "")
            if description:
                enum_items.append(f"{enum_id} ({description})")
            else:
                enum_items.append(enum_id)
        else:
            # Old format: simple strings
            enum_items.append(str(item))

    return "\n".join(f"• {item}" for item in enum_items)

def format_constraints(param_type_def):
    """
    Format validation constraints for display

    Args:
        param_type_def: Parameter type definition

    Returns:
        Formatted string describing constraints
    """
    constraints = []

    # Handle numeric constraints
    if "minimum" in param_type_def:
        constraints.append(f"min: {param_type_def['minimum']}")
    if "maximum" in param_type_def:
        constraints.append(f"max: {param_type_def['maximum']}")

    # Handle string constraints
    if "minLength" in param_type_def:
        constraints.append(f"min length: {param_type_def['minLength']}")
    if "maxLength" in param_type_def:
        constraints.append(f"max length: {param_type_def['maxLength']}")
    if "pattern" in param_type_def:
        constraints.append(f"pattern: {param_type_def['pattern']}")

    # Handle required field
    if param_type_def.get("required", False):
        constraints.append("required")

    return ", ".join(constraints) if constraints else "None"

def show_parameter_types(url):
    """
    Show all parameter type definitions
    """
    api = Api(url)
    config_api = api.config()

    # Get list of all parameter types
    try:
        param_type_names = config_api.list("parameter-types")
    except Exception as e:
        print(f"Error retrieving parameter types: {e}")
        return

    if len(param_type_names) == 0:
        print("No parameter types defined.")
        return

    for param_type_name in param_type_names:
        try:
            # Get the parameter type definition
            key = ConfigKey("parameter-types", param_type_name)
            type_def_value = config_api.get([key])[0].value
            param_type_def = json.loads(type_def_value)

            table = []
            table.append(("name", param_type_name))
            table.append(("description", param_type_def.get("description", "")))
            table.append(("type", param_type_def.get("type", "unknown")))

            # Show default value if present
            default = param_type_def.get("default")
            if default is not None:
                table.append(("default", str(default)))

            # Show enum values if present
            enum_list = param_type_def.get("enum")
            if enum_list:
                enum_str = format_enum_values(enum_list)
                table.append(("valid values", enum_str))

            # Show constraints
            constraints = format_constraints(param_type_def)
            if constraints != "None":
                table.append(("constraints", constraints))

            print(tabulate.tabulate(
                table,
                tablefmt="pretty",
                stralign="left",
            ))
            print()

        except Exception as e:
            print(f"Error retrieving parameter type '{param_type_name}': {e}")
            print()

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
        '-t', '--type',
        help='Show only the specified parameter type',
    )

    args = parser.parse_args()

    try:
        if args.type:
            # Show specific parameter type
            show_specific_parameter_type(args.api_url, args.type)
        else:
            # Show all parameter types
            show_parameter_types(args.api_url)

    except Exception as e:
        print("Exception:", e, flush=True)

def show_specific_parameter_type(url, param_type_name):
    """
    Show a specific parameter type definition
    """
    api = Api(url)
    config_api = api.config()

    try:
        # Get the parameter type definition
        key = ConfigKey("parameter-types", param_type_name)
        type_def_value = config_api.get([key])[0].value
        param_type_def = json.loads(type_def_value)

        table = []
        table.append(("name", param_type_name))
        table.append(("description", param_type_def.get("description", "")))
        table.append(("type", param_type_def.get("type", "unknown")))

        # Show default value if present
        default = param_type_def.get("default")
        if default is not None:
            table.append(("default", str(default)))

        # Show enum values if present
        enum_list = param_type_def.get("enum")
        if enum_list:
            enum_str = format_enum_values(enum_list)
            table.append(("valid values", enum_str))

        # Show constraints
        constraints = format_constraints(param_type_def)
        if constraints != "None":
            table.append(("constraints", constraints))

        print(tabulate.tabulate(
            table,
            tablefmt="pretty",
            stralign="left",
        ))

    except Exception as e:
        print(f"Error retrieving parameter type '{param_type_name}': {e}")

if __name__ == "__main__":
    main()