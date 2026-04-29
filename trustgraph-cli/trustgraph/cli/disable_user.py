"""
Disable a user.  Soft-deletes (enabled=false) and revokes all their
API keys.
"""

import argparse

from ._iam import DEFAULT_URL, DEFAULT_TOKEN, call_iam, run_main


def do_disable_user(args):
    req = {"operation": "disable-user", "user_id": args.user_id}
    if args.workspace:
        req["workspace"] = args.workspace
    call_iam(args.api_url, args.token, req)
    print(f"Disabled user {args.user_id}")


def main():
    parser = argparse.ArgumentParser(
        prog="tg-disable-user", description=__doc__,
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
        "--user-id", required=True, help="User id to disable",
    )
    parser.add_argument(
        "-w", "--workspace", default=None,
        help=(
            "Target workspace (admin only; defaults to caller's "
            "assigned workspace)"
        ),
    )
    run_main(do_disable_user, parser)


if __name__ == "__main__":
    main()
