"""
Change your own password.  Requires the current password.
"""

import argparse
import getpass

from ._iam import DEFAULT_URL, DEFAULT_TOKEN, call_auth, run_main


def do_change_password(args):
    current = args.current or getpass.getpass("Current password: ")
    new = args.new or getpass.getpass("New password: ")

    call_auth(
        args.api_url, "/api/v1/auth/change-password", args.token,
        {"current_password": current, "new_password": new},
    )
    print("Password changed.")


def main():
    parser = argparse.ArgumentParser(
        prog="tg-change-password", description=__doc__,
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
        "--current", default=None,
        help="Current password (prompted if omitted)",
    )
    parser.add_argument(
        "--new", default=None,
        help="New password (prompted if omitted)",
    )
    run_main(do_change_password, parser)


if __name__ == "__main__":
    main()
