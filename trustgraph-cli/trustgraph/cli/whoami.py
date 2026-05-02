"""
Show the authenticated caller's own user record.
"""

import argparse

import tabulate

from ._iam import DEFAULT_URL, DEFAULT_TOKEN, call_iam, run_main


def do_whoami(args):
    resp = call_iam(args.api_url, args.token, {"operation": "whoami"})
    user = resp.get("user")
    if not user:
        print("(no user record returned)")
        return

    rows = [
        ["id", user.get("id", "")],
        ["username", user.get("username", "")],
        ["name", user.get("name", "")],
        ["email", user.get("email", "")],
        ["workspace", user.get("workspace", "")],
        ["roles", ", ".join(user.get("roles", []))],
        ["enabled", "yes" if user.get("enabled") else "no"],
        [
            "must change password",
            "yes" if user.get("must_change_password") else "no",
        ],
        ["created", user.get("created", "")],
    ]
    print(tabulate.tabulate(rows, tablefmt="plain"))


def main():
    parser = argparse.ArgumentParser(
        prog="tg-whoami", description=__doc__,
    )
    parser.add_argument(
        "-u", "--api-url", default=DEFAULT_URL,
        help=f"API URL (default: {DEFAULT_URL})",
    )
    parser.add_argument(
        "-t", "--token", default=DEFAULT_TOKEN,
        help="Auth token (default: $TRUSTGRAPH_TOKEN)",
    )
    run_main(do_whoami, parser)


if __name__ == "__main__":
    main()
