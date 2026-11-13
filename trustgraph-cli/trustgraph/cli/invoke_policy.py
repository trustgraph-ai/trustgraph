"""
Invoke the policy engine with a subject and principal context.
Displays the policy attestation result.
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
        prog='tg-invoke-policy',
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
        '-e', '--evaluation-type',
        default="step-egress",
        choices=[
            "plan-preflight", "step-ingress",
            "step-egress", "artifact-egress",
        ],
        help='Evaluation type (default: step-egress)',
    )

    parser.add_argument(
        '-j', '--json',
        action='store_true',
        help='Output as JSON',
    )

    parser.add_argument(
        'subject_file',
        nargs='?',
        help='Path to JSON subject file (or read from stdin)',
    )

    parser.add_argument(
        '--principal',
        default=None,
        help='Path to JSON principal context file',
    )

    parser.add_argument(
        '--principal-user',
        default=None,
        help='Principal user IRI',
    )

    parser.add_argument(
        '--principal-roles',
        default=None,
        nargs='+',
        help='Principal roles',
    )

    args = parser.parse_args()

    if args.subject_file:
        with open(args.subject_file) as f:
            subject = json.load(f)
    else:
        if sys.stdin.isatty():
            print("Enter subject JSON (Ctrl-D to finish):", file=sys.stderr)
        subject = json.loads(sys.stdin.read())

    if args.principal:
        with open(args.principal) as f:
            principal = json.load(f)
    else:
        principal = {}
        if args.principal_user:
            principal["user"] = args.principal_user
        if args.principal_roles:
            principal["roles"] = args.principal_roles

    try:

        api = Api(
            url=args.url, token=args.token, workspace=args.workspace,
        )
        socket = api.socket()

        try:
            result = socket._send_request_sync(
                "policy", args.flow_id,
                {
                    "run-id": args.run_id,
                    "step-id": args.step_id,
                    "evaluation-type": args.evaluation_type,
                    "subject": subject,
                    "principal": principal,
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
            verdict = result.get("verdict", "?")
            disclosure = result.get("disclosure", "?")
            boundary = result.get("boundary-failure", False)
            matched = result.get("matched-rules", [])
            message = result.get("message", "")
            directives = result.get("redaction-directives", [])

            print(f"Verdict:          {verdict}")
            print(f"Disclosure:       {disclosure}")
            print(f"Boundary failure: {boundary}")

            if matched:
                print(f"Matched rules:    {', '.join(matched)}")

            if message:
                print(f"Message:          {message}")

            if directives:
                print(f"\nRedaction directives ({len(directives)}):")
                for d in directives:
                    print(
                        f"  [{d.get('method', '?')}] "
                        f"{d.get('field', '?')}"
                    )
                    if d.get("message"):
                        print(f"    {d['message']}")

    except Exception as e:
        print("Exception:", e, flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
