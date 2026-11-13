"""
Invoke the verification service with an artifact payload and expected
type.  Displays the verification result.
"""

import argparse
import json
import os
import sys
from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8888/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")


def main():

    parser = argparse.ArgumentParser(
        prog='tg-invoke-verification',
        description=__doc__,
    )

    parser.add_argument(
        '-u', '--url',
        default=default_url,
        help=f'API URL (default: {default_url})',
    )

    parser.add_argument(
        '-t', '--token',
        default=default_token,
        help='Authentication token (default: $TRUSTGRAPH_TOKEN)',
    )

    parser.add_argument(
        '-w', '--workspace',
        default=default_workspace,
        help=f'Workspace (default: {default_workspace})',
    )

    parser.add_argument(
        '-f', '--flow-id',
        default="default",
        help='Flow ID (default: default)',
    )

    parser.add_argument(
        '-r', '--run-id',
        default="run-cli",
        help='Run ID (default: run-cli)',
    )

    parser.add_argument(
        '-s', '--step-id',
        default="step-cli",
        help='Step ID (default: step-cli)',
    )

    parser.add_argument(
        '-j', '--json',
        action='store_true',
        help='Output as JSON',
    )

    parser.add_argument(
        'expected_type',
        help='Expected artifact type (e.g. TabularArtifact)',
    )

    parser.add_argument(
        'artifact_file',
        nargs='?',
        help='Path to JSON artifact file (or read from stdin)',
    )

    args = parser.parse_args()

    if args.artifact_file:
        with open(args.artifact_file) as f:
            artifact = json.load(f)
    else:
        if sys.stdin.isatty():
            print("Enter artifact JSON (Ctrl-D to finish):", file=sys.stderr)
        artifact = json.loads(sys.stdin.read())

    try:

        api = Api(
            url=args.url, token=args.token, workspace=args.workspace,
        )
        socket = api.socket()

        try:
            result = socket._send_request_sync(
                "verification", args.flow_id,
                {
                    "run-id": args.run_id,
                    "step-id": args.step_id,
                    "expected-type": args.expected_type,
                    "artifact": artifact,
                },
            )
        finally:
            socket.close()

        if result.get("error"):
            err = result["error"]
            print(
                f"Error: [{err.get('type', '?')}] {err.get('message', '?')}",
                file=sys.stderr,
            )
            sys.exit(1)

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            valid = result.get("valid", False)
            tier = result.get("tier", 0)
            violations = result.get("violations", [])

            status = "PASS" if valid else "FAIL"
            print(f"Result: {status} (tier {tier})")

            if violations:
                print(f"Violations: {len(violations)}")
                print()
                for v in violations:
                    sev = v.get("severity", "?").upper()
                    field = v.get("field", "?")
                    msg = v.get("message", "?")
                    print(f"  [{sev}] {field}: {msg}")
            else:
                print("No violations.")

    except Exception as e:
        print("Exception:", e, flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
