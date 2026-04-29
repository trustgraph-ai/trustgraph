"""
Create a user in the caller's workspace.  Prints the new user id.
"""

import argparse
import getpass
import sys

from ._iam import DEFAULT_URL, DEFAULT_TOKEN, call_iam, run_main


def do_create_user(args):
    password = args.password
    if not password:
        password = getpass.getpass(
            f"Password for new user {args.username}: "
        )

    user = {
        "username": args.username,
        "password": password,
        "roles": args.roles,
    }
    if args.name:
        user["name"] = args.name
    if args.email:
        user["email"] = args.email
    if args.must_change_password:
        user["must_change_password"] = True

    req = {"operation": "create-user", "user": user}
    if args.workspace:
        req["workspace"] = args.workspace
    resp = call_iam(args.api_url, args.token, req)

    rec = resp.get("user", {})
    print(f"User id: {rec.get('id', '')}", file=sys.stderr)
    print(f"Username: {rec.get('username', '')}", file=sys.stderr)
    print(f"Roles: {', '.join(rec.get('roles', []))}", file=sys.stderr)
    print(rec.get("id", ""))


def main():
    parser = argparse.ArgumentParser(
        prog="tg-create-user", description=__doc__,
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
        "--username", required=True, help="Username (unique in workspace)",
    )
    parser.add_argument(
        "--password", default=None,
        help="Password (prompted if omitted)",
    )
    parser.add_argument(
        "--name", default=None, help="Display name",
    )
    parser.add_argument(
        "--email", default=None, help="Email",
    )
    parser.add_argument(
        "--roles", nargs="+", default=["reader"],
        help="One or more role names (default: reader)",
    )
    parser.add_argument(
        "--must-change-password", action="store_true",
        help="Force password change on next login",
    )
    parser.add_argument(
        "-w", "--workspace", default=None,
        help=(
            "Target workspace (admin only; defaults to caller's "
            "assigned workspace)"
        ),
    )
    run_main(do_create_user, parser)


if __name__ == "__main__":
    main()
