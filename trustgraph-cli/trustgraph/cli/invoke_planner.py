"""
Invoke the planner service with a goal and display the resulting
execution plan.
"""

import argparse
import json
import os
import sys
import tabulate
from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8888/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")


def main():

    parser = argparse.ArgumentParser(
        prog='tg-invoke-planner',
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
        '-j', '--json',
        action='store_true',
        help='Output as JSON',
    )

    parser.add_argument(
        'goal',
        nargs='?',
        help='Goal for the planner (or read from stdin if not provided)',
    )

    args = parser.parse_args()

    goal = args.goal
    if goal is None:
        if sys.stdin.isatty():
            print("Enter goal (Ctrl-D to finish):", file=sys.stderr)
        goal = sys.stdin.read().strip()

    if not goal:
        print("Error: no goal provided", file=sys.stderr)
        sys.exit(1)

    try:

        api = Api(
            url=args.url, token=args.token, workspace=args.workspace,
        )
        socket = api.socket()

        try:
            result = socket._send_request_sync(
                "planner", args.flow_id,
                {
                    "run-id": args.run_id,
                    "goal": goal,
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
            plan_id = result.get("plan-id", "?")
            steps = result.get("steps", [])

            print(f"Plan: {plan_id}")
            print(f"Steps: {len(steps)}")
            print()

            table = []
            for s in steps:
                params = s.get("params", {})
                param_summary = []
                for k, v in params.items():
                    if isinstance(v, str):
                        param_summary.append(f"{k}={v}")
                    elif isinstance(v, dict):
                        atype = v.get("artifact-type", "?")
                        artifact = v.get("artifact", {})
                        if atype == "TextBlobArtifact":
                            text = artifact.get("text", "")
                            if len(text) > 60:
                                text = text[:57] + "..."
                            param_summary.append(
                                f"{k}=\"{text}\""
                            )
                        else:
                            param_summary.append(f"{k}: {atype}")
                    else:
                        param_summary.append(f"{k}={v}")

                table.append([
                    s.get("step-id", ""),
                    s.get("capability", ""),
                    ", ".join(s.get("depends-on", [])) or "-",
                    "; ".join(param_summary) or "-",
                ])

            print(tabulate.tabulate(
                table,
                headers=["Step", "Capability", "Depends On", "Params"],
                tablefmt="pretty",
                stralign="left",
            ))

    except Exception as e:
        print("Exception:", e, flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
