"""
Displays the current agent tool configurations

Shows all configured tools including their types:
- knowledge-query: Tools that query knowledge bases
- text-completion: Tools for text generation
- mcp-tool: References to MCP (Model Context Protocol) tools  
- prompt: Tools that execute prompt templates
"""

import argparse
import os
from trustgraph.api import Api, ConfigKey
import json
import tabulate
import textwrap

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')

def show_config(url):

    api = Api(url).config()

    values = api.get_values(type="tool")

    for item in values:

        id = item.key
        data = json.loads(item.value)

        tp = data["type"]

        table = []

        table.append(("id", id))
        table.append(("name", data["name"]))
        table.append(("description", data["description"]))
        table.append(("type", tp))

        if tp == "mcp-tool":
            table.append(("mcp-tool", data["mcp-tool"]))
          
        if tp == "knowledge-query":
            table.append(("collection", data["collection"]))

        if tp == "prompt":
            table.append(("template", data["template"]))
            for n, arg in enumerate(data["arguments"]):
                table.append((
                    f"arg {n}",
                    f"{arg['name']}: {arg['type']}\n{arg['description']}"
                ))

        print()

        print(tabulate.tabulate(
            table,
            tablefmt="pretty",
            maxcolwidths=[None, 70],
            stralign="left"
        ))
        
    print()

def main():

    parser = argparse.ArgumentParser(
        prog='tg-show-tools',
        description=__doc__,
    )

    parser.add_argument(
        '-u', '--api-url',
        default=default_url,
        help=f'API URL (default: {default_url})',
    )

    args = parser.parse_args()

    try:

        show_config(
            url=args.api_url,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()