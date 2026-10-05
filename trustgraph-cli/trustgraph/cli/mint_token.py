"""
Mint a JWT containing a caller-supplied UserContext.  Requires an
admin auth token.  Prints the resulting JWT to stdout.
"""

import argparse
import json
import sys

from ._iam import DEFAULT_URL, DEFAULT_TOKEN, call_iam, run_main


def do_mint_token(args):
    try:
        user_context = json.loads(args.user_context)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON for --user-context: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(user_context, dict):
        print("--user-context must be a JSON object", file=sys.stderr)
        sys.exit(1)

    req = {
        "operation": "mint-token",
        "workspace": args.workspace,
        "user_context_json": json.dumps(user_context),
    }

    if args.user_id:
        req["user_id"] = args.user_id
    elif args.username:
        req["username"] = args.username
    # --self: leave both empty; the gateway populates actor

    resp = call_iam(args.api_url, args.token, req)

    jwt = resp.get("jwt", "")
    expires = resp.get("jwt_expires", "")

    if expires:
        print(f"JWT expires: {expires}", file=sys.stderr)
    print(jwt)


def main():
    parser = argparse.ArgumentParser(
        prog="tg-mint-token", description=__doc__,
    )
    parser.add_argument(
        "-u", "--api-url", default=DEFAULT_URL,
        help=f"API URL (default: {DEFAULT_URL})",
    )
    parser.add_argument(
        "-t", "--token", default=DEFAULT_TOKEN,
        help="Admin auth token (JWT or API key)",
    )
    parser.add_argument(
        "-w", "--workspace", required=True,
        help="Target workspace for the minted token",
    )
    parser.add_argument(
        "--user-context", required=True,
        help="UserContext as a JSON string",
    )

    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument(
        "--user-id",
        help="User ID (UUID) for the minted token's subject",
    )
    target.add_argument(
        "--username",
        help="Username to resolve to a user ID",
    )
    target.add_argument(
        "--self", dest="use_self", action="store_true",
        help="Mint token for the caller's own user ID",
    )

    run_main(do_mint_token, parser)


if __name__ == "__main__":
    main()
