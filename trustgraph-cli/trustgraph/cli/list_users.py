"""
List users in the caller's workspace.
"""

import argparse

import tabulate

from ._iam import DEFAULT_URL, DEFAULT_TOKEN, call_iam, run_main


def do_list_users(args):
    req = {"operation": "list-users"}
    if args.workspace:
        req["workspace"] = args.workspace
    resp = call_iam(args.api_url, args.token, req)

    users = resp.get("users", [])
    if not users:
        print("No users.")
        return

    rows = [
        [
            u.get("id", ""),
            u.get("username", ""),
            u.get("name", ""),
            ", ".join(u.get("roles", [])),
            "yes" if u.get("enabled") else "no",
            "yes" if u.get("must_change_password") else "no",
        ]
        for u in users
    ]
    print(tabulate.tabulate(
        rows,
        headers=["id", "username", "name", "roles", "enabled", "change-pw"],
        tablefmt="pretty",
        stralign="left",
    ))


def main():
    parser = argparse.ArgumentParser(
        prog="tg-list-users", description=__doc__,
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
        "-w", "--workspace", default=None,
        help=(
            "Target workspace (admin only; defaults to caller's "
            "assigned workspace)"
        ),
    )
    run_main(do_list_users, parser)


if __name__ == "__main__":
    main()
