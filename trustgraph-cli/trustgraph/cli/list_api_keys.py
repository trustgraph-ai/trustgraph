"""
List the API keys for a user.
"""

import argparse

import tabulate

from ._iam import DEFAULT_URL, DEFAULT_TOKEN, call_iam, run_main


def do_list_api_keys(args):
    req = {"operation": "list-api-keys", "user_id": args.user_id}
    if args.workspace:
        req["workspace"] = args.workspace
    resp = call_iam(args.api_url, args.token, req)

    keys = resp.get("api_keys", [])
    if not keys:
        print("No keys.")
        return

    rows = [
        [
            k.get("id", ""),
            k.get("name", ""),
            k.get("prefix", ""),
            k.get("created", ""),
            k.get("last_used", "") or "—",
            k.get("expires", "") or "never",
        ]
        for k in keys
    ]
    print(tabulate.tabulate(
        rows,
        headers=["id", "name", "prefix", "created", "last used", "expires"],
        tablefmt="pretty",
        stralign="left",
    ))


def main():
    parser = argparse.ArgumentParser(
        prog="tg-list-api-keys", description=__doc__,
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
        "--user-id", required=True,
        help="Owner user id",
    )
    parser.add_argument(
        "-w", "--workspace", default=None,
        help=(
            "Target workspace (admin only; defaults to caller's "
            "assigned workspace)"
        ),
    )
    run_main(do_list_api_keys, parser)


if __name__ == "__main__":
    main()
