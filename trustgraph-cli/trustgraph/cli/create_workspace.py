"""
Create a workspace (system-level; requires admin).
"""

import argparse

from ._iam import DEFAULT_URL, DEFAULT_TOKEN, call_iam, run_main


def do_create_workspace(args):
    ws = {"id": args.workspace_id, "enabled": True}
    if args.name:
        ws["name"] = args.name

    resp = call_iam(args.api_url, args.token, {
        "operation": "create-workspace",
        "workspace_record": ws,
    })
    rec = resp.get("workspace", {})
    print(f"Workspace created: {rec.get('id', '')}")


def main():
    parser = argparse.ArgumentParser(
        prog="tg-create-workspace", description=__doc__,
    )
    parser.add_argument(
        "-u", "--api-url", default=DEFAULT_URL,
        help=f"API URL (default: {DEFAULT_URL})",
    )
    parser.add_argument(
        "-t", "--token", default=DEFAULT_TOKEN,
        help="Auth token (default: $TRUSTGRAPH_TOKEN)",
    )
    parser.add_argument(
        "--workspace-id", required=True,
        help="New workspace id (must not start with '_')",
    )
    parser.add_argument(
        "--name", default=None, help="Display name",
    )
    run_main(do_create_workspace, parser)


if __name__ == "__main__":
    main()
