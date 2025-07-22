"""
Deletes tools from the TrustGraph system.
Removes tool configurations by ID from the agent configuration
and updates the tool index accordingly.
"""

import argparse
import os
from trustgraph.api import Api, ConfigKey, ConfigValue
import json
import textwrap

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')

def delete_tool(
        url : str,
        id : str,
):

    api = Api(url).config()

    # Check if the tool configuration exists
    try:
        tool_values = api.get([
            ConfigKey(type="tool", key=id)
        ])
        
        if not tool_values or not tool_values[0].value:
            print(f"Tool configuration for '{id}' not found.")
            return False
            
    except Exception as e:
        print(f"Tool configuration for '{id}' not found.")
        return False

    # Delete the tool configuration and update the index
    try:

        # Delete the tool configuration
        api.delete([
            ConfigKey(type="tool", key=id)
        ])
        
        print(f"Tool '{id}' deleted successfully.")
        return True
        
    except Exception as e:
        print(f"Error deleting tool '{id}': {e}")
        return False

def main():

    parser = argparse.ArgumentParser(
        prog='tg-delete-tool',
        description=__doc__,
        epilog=textwrap.dedent('''
            This utility removes tool configurations from the TrustGraph system.
            It removes the tool from both the tool index and deletes the tool
            configuration. Once deleted, the tool will no longer be available for use.
            
            Examples:
              %(prog)s --id weather
              %(prog)s --id calculator
              %(prog)s --api-url http://localhost:9000/ --id file-reader
        ''').strip(),
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '-u', '--api-url',
        default=default_url,
        help=f'API URL (default: {default_url})',
    )

    parser.add_argument(
        '--id',
        required=True,
        help='Tool ID to delete',
    )

    args = parser.parse_args()

    try:

        if not args.id:
            raise RuntimeError("Must specify --id for tool to delete")

        delete_tool(
            url=args.api_url, 
            id=args.id
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()