"""
Delete a user.  Removes the user record, their username lookup,
and all their API keys.  The freed username becomes available for
re-use.

Irreversible.  Use tg-disable-user if you want to preserve the
record (audit trail, username squatting protection).
"""

import argparse

from ._iam import DEFAULT_URL, DEFAULT_TOKEN, call_iam, run_main


def do_delete_user(args):
    if not args.yes:
        confirm = input(
            f"Delete user {args.user_id}?  This is irreversible. "
            f"[type 'yes' to confirm]: "
        )
        if confirm.strip() != "yes":
            print("Aborted.")
            return

    req = {"operation": "delete-user", "user_id": args.user_id}
    if args.workspace:
        req["workspace"] = args.workspace
    call_iam(args.api_url, args.token, req)
    print(f"Deleted user {args.user_id}")


def main():
    parser = argparse.ArgumentParser(
        prog="tg-delete-user", description=__doc__,
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
        "--user-id", required=True, help="User id to delete",
    )
    parser.add_argument(
        "-w", "--workspace", default=None,
        help=(
            "Target workspace (admin only; defaults to caller's "
            "assigned workspace)"
        ),
    )
    parser.add_argument(
        "--yes", action="store_true",
        help="Skip the interactive confirmation prompt",
    )
    run_main(do_delete_user, parser)


if __name__ == "__main__":
    main()
