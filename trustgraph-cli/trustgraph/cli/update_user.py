"""
Update a user's profile fields: name, email, roles, enabled flag,
must-change-password flag.

Username is immutable — create a new user and disable the old one
to effect a username change.  Password changes go through
``tg-change-password`` (self-service) or ``tg-reset-password``
(admin-driven).

Only the fields you supply are changed; omitted fields are left
untouched on the user record.  An empty ``--roles`` is rejected by
iam-svc (a user must have at least one role); to demote a user use
``tg-disable-user``.
"""

import argparse
import sys

from ._iam import DEFAULT_URL, DEFAULT_TOKEN, call_iam, run_main


def _parse_bool(s):
    if s is None:
        return None
    s = s.strip().lower()
    if s in ("yes", "y", "true", "t", "1"):
        return True
    if s in ("no", "n", "false", "f", "0"):
        return False
    raise argparse.ArgumentTypeError(
        f"expected yes/no, got {s!r}"
    )


def do_update_user(args):
    user = {}
    if args.name is not None:
        user["name"] = args.name
    if args.email is not None:
        user["email"] = args.email
    if args.roles is not None:
        user["roles"] = args.roles
    if args.enabled is not None:
        user["enabled"] = args.enabled
    if args.must_change_password is not None:
        user["must_change_password"] = args.must_change_password

    if not user:
        print(
            "tg-update-user: nothing to change — supply at least "
            "one of --name / --email / --roles / --enabled / "
            "--must-change-password",
            file=sys.stderr,
        )
        sys.exit(2)

    req = {
        "operation": "update-user",
        "user_id": args.user_id,
        "user": user,
    }
    if args.workspace:
        req["workspace"] = args.workspace
    resp = call_iam(args.api_url, args.token, req)

    rec = resp.get("user", {})
    print(f"id        : {rec.get('id', '')}")
    print(f"username  : {rec.get('username', '')}")
    print(f"name      : {rec.get('name', '')}")
    print(f"email     : {rec.get('email', '')}")
    print(f"workspace : {rec.get('workspace', '')}")
    print(f"roles     : {', '.join(rec.get('roles', []))}")
    print(f"enabled   : {'yes' if rec.get('enabled') else 'no'}")
    print(
        f"must-change-pw: "
        f"{'yes' if rec.get('must_change_password') else 'no'}"
    )


def main():
    parser = argparse.ArgumentParser(
        prog="tg-update-user", description=__doc__,
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
        "--user-id", required=True, help="Target user id",
    )
    parser.add_argument(
        "--name", default=None, help="New display name",
    )
    parser.add_argument(
        "--email", default=None, help="New email",
    )
    parser.add_argument(
        "--roles", nargs="+", default=None,
        help="Replacement role list (e.g. --roles reader writer)",
    )
    parser.add_argument(
        "--enabled", type=_parse_bool, default=None,
        help="Set enabled flag (yes/no)",
    )
    parser.add_argument(
        "--must-change-password", type=_parse_bool, default=None,
        help="Set must-change-password flag (yes/no)",
    )
    parser.add_argument(
        "-w", "--workspace", default=None,
        help=(
            "Optional workspace integrity check — when supplied, "
            "iam-svc verifies the target user's home workspace "
            "matches"
        ),
    )
    run_main(do_update_user, parser)


if __name__ == "__main__":
    main()
