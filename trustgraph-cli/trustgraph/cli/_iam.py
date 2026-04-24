"""
Shared helpers for IAM CLI tools.

All IAM operations go through the gateway's ``/api/v1/iam`` forwarder,
with the three public auth operations (``login``, ``bootstrap``,
``change-password``) served via ``/api/v1/auth/...`` instead.  These
helpers encapsulate the HTTP plumbing so each CLI can stay focused
on its own argument parsing and output formatting.
"""

import json
import os
import sys

import requests


DEFAULT_URL = os.getenv("TRUSTGRAPH_URL", "http://localhost:8088/")
DEFAULT_TOKEN = os.getenv("TRUSTGRAPH_TOKEN", None)


def _fmt_error(resp_json):
    err = resp_json.get("error", {})
    if isinstance(err, dict):
        t = err.get("type", "")
        m = err.get("message", "")
        return f"{t}: {m}" if t else m or "error"
    return str(err)


def _post(url, path, token, body):
    endpoint = url.rstrip("/") + path
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    resp = requests.post(
        endpoint, headers=headers, data=json.dumps(body),
    )

    if resp.status_code != 200:
        try:
            payload = resp.json()
            detail = _fmt_error(payload)
        except Exception:
            detail = resp.text
        raise RuntimeError(f"HTTP {resp.status_code}: {detail}")

    body = resp.json()
    if "error" in body:
        raise RuntimeError(_fmt_error(body))
    return body


def call_iam(url, token, request):
    """Forward an IAM request through ``/api/v1/iam``.  ``request`` is
    the ``IamRequest`` dict shape."""
    return _post(url, "/api/v1/iam", token, request)


def call_auth(url, path, token, body):
    """Hit one of the public auth endpoints
    (``/api/v1/auth/login``, ``/api/v1/auth/change-password``, etc.).
    ``token`` is optional — login and bootstrap don't need one."""
    return _post(url, path, token, body)


def run_main(fn, parser):
    """Standard error-handling wrapper for CLI main() bodies."""
    args = parser.parse_args()
    try:
        fn(args)
    except Exception as e:
        print("Exception:", e, file=sys.stderr, flush=True)
        sys.exit(1)
