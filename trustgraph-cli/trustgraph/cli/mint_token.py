"""
Mint a JWT containing a caller-supplied UserContext.  Requires an
admin auth token.  Prints the resulting JWT to stdout.
"""

import argparse
import json
import sys

from ._iam import DEFAULT_URL, DEFAULT_TOKEN, call_auth, run_main


def do_mint_token(args):
    try:
        user_context = json.loads(args.user_context)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON for --user-context: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(user_context, dict):
        print("--user-context must be a JSON object", file=sys.stderr)
        sys.exit(1)

    body = {
        "user_id": args.user_id,
        "workspace": args.workspace,
        "user_context": user_context,
    }

    resp = call_auth(
        args.api_url, "/api/v1/auth/mint-token", args.token, body,
    )

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
        "--user-id", required=True,
        help="User ID for the minted token's subject",
    )
    parser.add_argument(
        "-w", "--workspace", required=True,
        help="Target workspace for the minted token",
    )
    parser.add_argument(
        "--user-context", required=True,
        help="UserContext as a JSON string",
    )
    run_main(do_mint_token, parser)


if __name__ == "__main__":
    main()
