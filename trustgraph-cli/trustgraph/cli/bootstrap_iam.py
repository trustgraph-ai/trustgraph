"""
Bootstraps the IAM service.  Only works when iam-svc is running in
bootstrap mode with empty tables.  Prints the initial admin API key
to stdout.

This is a one-time, trust-sensitive operation.  The resulting token
is shown once and never again — capture it on use.  Rotate and
revoke it as soon as a real admin API key has been issued.
"""

import argparse
import json
import os
import sys

import requests

default_url = os.getenv("TRUSTGRAPH_URL", "http://localhost:8088/")


def bootstrap(url):

    # Unauthenticated public endpoint — IAM refuses the bootstrap
    # operation unless the service is running in bootstrap mode with
    # empty tables, so the safety gate lives on the server side.
    endpoint = url.rstrip("/") + "/api/v1/auth/bootstrap"

    headers = {"Content-Type": "application/json"}

    resp = requests.post(
        endpoint,
        headers=headers,
        data=json.dumps({}),
    )

    if resp.status_code != 200:
        raise RuntimeError(
            f"HTTP {resp.status_code}: {resp.text}"
        )

    body = resp.json()

    if "error" in body:
        raise RuntimeError(
            f"IAM {body['error'].get('type', 'error')}: "
            f"{body['error'].get('message', '')}"
        )

    api_key = body.get("bootstrap_admin_api_key")
    user_id = body.get("bootstrap_admin_user_id")

    if not api_key:
        raise RuntimeError(
            "IAM response did not contain a bootstrap token — the "
            "service may already be bootstrapped, or may be running "
            "in token mode."
        )

    return user_id, api_key


def main():

    parser = argparse.ArgumentParser(
        prog="tg-bootstrap-iam",
        description=__doc__,
    )

    parser.add_argument(
        "-u", "--api-url",
        default=default_url,
        help=f"API URL (default: {default_url})",
    )

    args = parser.parse_args()

    try:
        user_id, api_key = bootstrap(args.api_url)
    except Exception as e:
        print("Exception:", e, file=sys.stderr, flush=True)
        sys.exit(1)

    # Stdout gets machine-readable output (the key).  Any operator
    # context goes to stderr.
    print(f"Admin user id: {user_id}", file=sys.stderr)
    print(
        "Admin API key (shown once, capture now):",
        file=sys.stderr,
    )
    print(api_key)


if __name__ == "__main__":
    main()
