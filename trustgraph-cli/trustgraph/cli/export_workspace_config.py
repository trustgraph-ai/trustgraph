"""
Exports a curated subset of a workspace's configuration to a JSON file
for later reload into another workspace (useful for cloning test setups).

The subset covers the config types that define workspace behaviour:
mcp-tool, tool, flow-blueprint, token-cost, agent-pattern,
agent-task-type, parameter-type, interface-description, prompt.
"""

import argparse
import os
import json
import sys
from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")

EXPORT_TYPES = [
    "mcp-tool",
    "tool",
    "flow-blueprint",
    "token-cost",
    "agent-pattern",
    "agent-task-type",
    "parameter-type",
    "interface-description",
    "prompt",
]


def export_workspace_config(url, workspace, output, token=None):

    api = Api(url, token=token, workspace=workspace).config()

    config, version = api.all()

    subset = {}
    for t in EXPORT_TYPES:
        if t in config:
            subset[t] = config[t]

    payload = {
        "source_workspace": workspace,
        "source_version": version,
        "config": subset,
    }

    if output == "-":
        json.dump(payload, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        with open(output, "w") as f:
            json.dump(payload, f, indent=2)

    total = sum(len(v) for v in subset.values())
    print(
        f"Exported {total} items across {len(subset)} types "
        f"from workspace '{workspace}' (version {version}).",
        file=sys.stderr,
    )


def main():

    parser = argparse.ArgumentParser(
        prog='tg-export-workspace-config',
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
        help=f'Source workspace (default: {default_workspace})',
    )

    parser.add_argument(
        '-o', '--output',
        required=True,
        help='Output JSON file path (use "-" for stdout)',
    )

    args = parser.parse_args()

    try:

        export_workspace_config(
            url=args.api_url,
            workspace=args.workspace,
            output=args.output,
            token=args.token,
        )

    except Exception as e:

        print("Exception:", e, flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
