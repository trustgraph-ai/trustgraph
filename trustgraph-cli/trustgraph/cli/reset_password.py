"""
Admin: reset another user's password.  Prints a one-time temporary
password to stdout.  The user is forced to change it on next login.
"""

import argparse
import sys

from ._iam import DEFAULT_URL, DEFAULT_TOKEN, call_iam, run_main


def do_reset_password(args):
    req = {"operation": "reset-password", "user_id": args.user_id}
    if args.workspace:
        req["workspace"] = args.workspace
    resp = call_iam(args.api_url, args.token, req)

    tmp = resp.get("temporary_password", "")
    if not tmp:
        raise RuntimeError(
            "IAM returned no temporary password — unexpected"
        )
    print("Temporary password (shown once, capture now):", file=sys.stderr)
    print(tmp)


def main():
    parser = argparse.ArgumentParser(
        prog="tg-reset-password", description=__doc__,
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
        help="Target user id",
    )
    parser.add_argument(
        "-w", "--workspace", default=None,
        help=(
            "Target workspace (admin only; defaults to caller's "
            "assigned workspace)"
        ),
    )
    run_main(do_reset_password, parser)


if __name__ == "__main__":
    main()
