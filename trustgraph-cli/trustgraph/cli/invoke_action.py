"""
Invoke the action worker with a capability and parameters.
Displays the resulting artifact.
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
        prog='tg-invoke-action',
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
        '-p', '--param',
        action='append',
        default=[],
        metavar='KEY=VALUE',
        help='Step parameter (repeatable)',
    )

    parser.add_argument(
        '-i', '--input-artifact',
        action='append',
        default=[],
        metavar='TYPE:FILE',
        help='Input artifact as TYPE:FILE e.g. TabularArtifact:data.json (repeatable)',
    )

    parser.add_argument(
        'capability',
        help='Capability to invoke (e.g. erp-finance-query)',
    )

    args = parser.parse_args()

    params = {}
    for p in args.param:
        if '=' not in p:
            print(f"Error: parameter must be KEY=VALUE: {p}", file=sys.stderr)
            sys.exit(1)
        key, value = p.split('=', 1)
        params[key] = value

    input_artifacts = []
    for spec in args.input_artifact:
        if ':' not in spec:
            print(
                f"Error: input artifact must be TYPE:FILE: {spec}",
                file=sys.stderr,
            )
            sys.exit(1)
        artifact_type, path = spec.split(':', 1)
        with open(path) as f:
            input_artifacts.append({
                "artifact-type": artifact_type,
                "artifact": json.load(f),
            })

    try:

        api = Api(
            url=args.url, token=args.token, workspace=args.workspace,
        )
        socket = api.socket()

        try:
            result = socket._send_request_sync(
                "action", args.flow_id,
                {
                    "run-id": args.run_id,
                    "step-id": args.step_id,
                    "capability": args.capability,
                    "params": params,
                    "input-artifacts": input_artifacts,
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
            artifact_type = result.get("artifact-type", "?")
            artifact = result.get("artifact", {})

            print(f"Artifact type: {artifact_type}")
            print()

            if artifact_type == "TabularArtifact":
                _print_tabular(artifact)
            elif artifact_type == "TextBlobArtifact":
                _print_text_blob(artifact)
            elif artifact_type == "SubgraphArtifact":
                _print_subgraph(artifact)
            elif artifact_type == "ReportArtifact":
                _print_report(artifact)
            else:
                print(json.dumps(artifact, indent=2))

    except Exception as e:
        print("Exception:", e, flush=True)
        sys.exit(1)


def _print_tabular(artifact):
    columns = artifact.get("columns", [])
    rows = artifact.get("rows", [])
    col_names = [c.get("name", "?") for c in columns]

    if not col_names:
        print("(empty table)")
        return

    try:
        import tabulate
        table = [
            [row.get(c, "") for c in col_names]
            for row in rows
        ]
        print(tabulate.tabulate(
            table,
            headers=col_names,
            tablefmt="pretty",
            stralign="left",
        ))
    except ImportError:
        print(" | ".join(col_names))
        print(" | ".join("---" for _ in col_names))
        for row in rows:
            print(" | ".join(str(row.get(c, "")) for c in col_names))

    print(f"\n{len(rows)} rows")


def _print_text_blob(artifact):
    text = artifact.get("text", "")
    print(text)


def _print_subgraph(artifact):
    triples = artifact.get("triples", [])
    summary = artifact.get("summary", "")

    if summary:
        print("Summary:")
        print(summary)
        print()

    print(f"Triples ({len(triples)}):")
    for t in triples[:20]:
        s = t.get("s", "?")
        p = t.get("p", "?")
        o = t.get("o", "?")
        print(f"  {s}  {p}  {o}")
    if len(triples) > 20:
        print(f"  ... and {len(triples) - 20} more")


def _print_report(artifact):
    fmt = artifact.get("format", "?")
    narrative = artifact.get("narrative", "")
    print(f"Format: {fmt}")
    print()
    print(narrative)


if __name__ == "__main__":
    main()
