"""
Create an API key for a user.  Prints the plaintext key to stdout —
shown once only.
"""

import argparse
import sys

from ._iam import DEFAULT_URL, DEFAULT_TOKEN, call_iam, run_main


def do_create_api_key(args):
    key = {
        "user_id": args.user_id,
        "name": args.name,
    }
    if args.expires:
        key["expires"] = args.expires

    req = {"operation": "create-api-key", "key": key}
    if args.workspace:
        req["workspace"] = args.workspace
    resp = call_iam(args.api_url, args.token, req)

    plaintext = resp.get("api_key_plaintext", "")
    rec = resp.get("api_key", {})
    print(f"Key id: {rec.get('id', '')}", file=sys.stderr)
    print(f"Name: {rec.get('name', '')}", file=sys.stderr)
    print(f"Prefix: {rec.get('prefix', '')}", file=sys.stderr)
    print(
        "API key (shown once, capture now):", file=sys.stderr,
    )
    print(plaintext)


def main():
    parser = argparse.ArgumentParser(
        prog="tg-create-api-key", description=__doc__,
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
        "--name", required=True,
        help="Operator-facing label (e.g. 'laptop', 'ci')",
    )
    parser.add_argument(
        "--expires", default=None,
        help="ISO-8601 expiry (optional; empty = no expiry)",
    )
    parser.add_argument(
        "-w", "--workspace", default=None,
        help=(
            "Target workspace (admin only; defaults to caller's "
            "assigned workspace)"
        ),
    )
    run_main(do_create_api_key, parser)


if __name__ == "__main__":
    main()
