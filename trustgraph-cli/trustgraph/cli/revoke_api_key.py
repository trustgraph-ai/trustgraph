"""
Revoke an API key by id.
"""

import argparse

from ._iam import DEFAULT_URL, DEFAULT_TOKEN, call_iam, run_main


def do_revoke_api_key(args):
    req = {"operation": "revoke-api-key", "key_id": args.key_id}
    if args.workspace:
        req["workspace"] = args.workspace
    call_iam(args.api_url, args.token, req)
    print(f"Revoked key {args.key_id}")


def main():
    parser = argparse.ArgumentParser(
        prog="tg-revoke-api-key", description=__doc__,
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
        "--key-id", required=True, help="Key id to revoke",
    )
    parser.add_argument(
        "-w", "--workspace", default=None,
        help=(
            "Target workspace (admin only; defaults to caller's "
            "assigned workspace)"
        ),
    )
    run_main(do_revoke_api_key, parser)


if __name__ == "__main__":
    main()
