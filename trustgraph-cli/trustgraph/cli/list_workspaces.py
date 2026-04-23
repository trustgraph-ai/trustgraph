"""
List workspaces (system-level; requires admin).
"""

import argparse

import tabulate

from ._iam import DEFAULT_URL, DEFAULT_TOKEN, call_iam, run_main


def do_list_workspaces(args):
    resp = call_iam(
        args.api_url, args.token, {"operation": "list-workspaces"},
    )
    workspaces = resp.get("workspaces", [])
    if not workspaces:
        print("No workspaces.")
        return
    rows = [
        [
            w.get("id", ""),
            w.get("name", ""),
            "yes" if w.get("enabled") else "no",
            w.get("created", ""),
        ]
        for w in workspaces
    ]
    print(tabulate.tabulate(
        rows,
        headers=["id", "name", "enabled", "created"],
        tablefmt="pretty",
        stralign="left",
    ))


def main():
    parser = argparse.ArgumentParser(
        prog="tg-list-workspaces", description=__doc__,
    )
    parser.add_argument(
        "-u", "--api-url", default=DEFAULT_URL,
        help=f"API URL (default: {DEFAULT_URL})",
    )
    parser.add_argument(
        "-t", "--token", default=DEFAULT_TOKEN,
        help="Auth token (default: $TRUSTGRAPH_TOKEN)",
    )
    run_main(do_list_workspaces, parser)


if __name__ == "__main__":
    main()
