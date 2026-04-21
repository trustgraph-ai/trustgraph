"""
Imports a workspace-config dump produced by tg-export-workspace-config
into a target workspace. Writes mcp-tool, tool, flow-blueprint,
token-cost, agent-pattern, agent-task-type, parameter-type,
interface-description and prompt items verbatim.

Existing items with the same (type, key) are overwritten.
"""

import argparse
import os
import json
import sys
from trustgraph.api import Api
from trustgraph.api.types import ConfigValue

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")

IMPORT_TYPES = {
    "mcp-tool",
    "tool",
    "flow-blueprint",
    "token-cost",
    "agent-pattern",
    "agent-task-type",
    "parameter-type",
    "interface-description",
    "prompt",
}


def import_workspace_config(url, workspace, input_path, token=None,
                            dry_run=False):

    if input_path == "-":
        payload = json.load(sys.stdin)
    else:
        with open(input_path, "r") as f:
            payload = json.load(f)

    # Accept both the wrapped export format and a bare {type: {key: value}}
    # dict, so hand-written files are also loadable.
    if isinstance(payload, dict) and "config" in payload \
            and isinstance(payload["config"], dict):
        config = payload["config"]
        source = payload.get("source_workspace")
    else:
        config = payload
        source = None

    skipped_types = set(config.keys()) - IMPORT_TYPES
    if skipped_types:
        print(
            f"Ignoring unsupported types: {sorted(skipped_types)}",
            file=sys.stderr,
        )

    values = []
    for t in IMPORT_TYPES:
        items = config.get(t, {})
        for key, value in items.items():
            values.append(ConfigValue(type=t, key=key, value=value))

    if not values:
        print("Nothing to import.", file=sys.stderr)
        return

    if dry_run:
        print(
            f"[dry-run] would import {len(values)} items into "
            f"workspace '{workspace}'"
            + (f" (from '{source}')" if source else "")
        )
        return

    api = Api(url, token=token, workspace=workspace).config()
    api.put(values)

    print(
        f"Imported {len(values)} items into workspace '{workspace}'"
        + (f" (from '{source}')." if source else "."),
    )


def main():

    parser = argparse.ArgumentParser(
        prog='tg-import-workspace-config',
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
        help=f'Target workspace (default: {default_workspace})',
    )

    parser.add_argument(
        '-i', '--input',
        required=True,
        help='Input JSON file path (use "-" for stdin)',
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Parse and validate the input without writing anything',
    )

    args = parser.parse_args()

    try:

        import_workspace_config(
            url=args.api_url,
            workspace=args.workspace,
            input_path=args.input,
            token=args.token,
            dry_run=args.dry_run,
        )

    except Exception as e:

        print("Exception:", e, flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
