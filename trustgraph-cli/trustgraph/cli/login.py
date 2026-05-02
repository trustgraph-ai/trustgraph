"""
Log in with username / password.  Prints the resulting JWT to
stdout so it can be captured for subsequent CLI use.
"""

import argparse
import getpass
import sys

from ._iam import DEFAULT_URL, call_auth, run_main


def do_login(args):
    password = args.password
    if not password:
        password = getpass.getpass(f"Password for {args.username}: ")

    body = {
        "username": args.username,
        "password": password,
    }
    if args.workspace:
        body["workspace"] = args.workspace

    resp = call_auth(args.api_url, "/api/v1/auth/login", None, body)

    jwt = resp.get("jwt", "")
    expires = resp.get("jwt_expires", "")

    if expires:
        print(f"JWT expires: {expires}", file=sys.stderr)
    # Machine-readable on stdout.
    print(jwt)


def main():
    parser = argparse.ArgumentParser(
        prog="tg-login", description=__doc__,
    )
    parser.add_argument(
        "-u", "--api-url", default=DEFAULT_URL,
        help=f"API URL (default: {DEFAULT_URL})",
    )
    parser.add_argument(
        "--username", required=True, help="Username",
    )
    parser.add_argument(
        "--password", default=None,
        help="Password (prompted if omitted)",
    )
    parser.add_argument(
        "-w", "--workspace", default=None,
        help=(
            "Optional workspace to log in against.  Defaults to "
            "the user's assigned workspace."
        ),
    )
    run_main(do_login, parser)


if __name__ == "__main__":
    main()
