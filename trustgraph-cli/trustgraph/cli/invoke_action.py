"""
Invoke the action worker with a capability and parameters.
Displays the resulting artifacts.
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
        metavar='NAME:TYPE:VALUE',
        help=(
            'Input parameter as NAME:TYPE:VALUE '
            'e.g. question:TextBlobArtifact:\'{"text": "hello"}\' '
            '(repeatable)'
        ),
    )

    parser.add_argument(
        '-i', '--input',
        action='append',
        default=[],
        metavar='NAME:TYPE:FILE',
        help=(
            'Input from file as NAME:TYPE:FILE '
            'e.g. data:TabularArtifact:data.json (repeatable)'
        ),
    )

    parser.add_argument(
        '-T', '--text',
        action='append',
        default=[],
        metavar='NAME=VALUE',
        help=(
            'Text input shorthand as NAME=VALUE '
            'e.g. question="What are total expenses?" (repeatable)'
        ),
    )

    parser.add_argument(
        'capability',
        help='Capability to invoke (e.g. llm-synthesis)',
    )

    args = parser.parse_args()

    params = {}

    for spec in args.param:
        parts = spec.split(':', 2)
        if len(parts) != 3:
            print(
                f"Error: parameter must be NAME:TYPE:VALUE: {spec}",
                file=sys.stderr,
            )
            sys.exit(1)
        name, artifact_type, value = parts
        try:
            artifact = json.loads(value)
        except json.JSONDecodeError as e:
            print(
                f"Error: value for '{name}' is not valid JSON: {e}",
                file=sys.stderr,
            )
            sys.exit(1)
        params[name] = {
            "artifact-type": artifact_type,
            "artifact": artifact,
        }

    for spec in args.input:
        parts = spec.split(':', 2)
        if len(parts) != 3:
            print(
                f"Error: input must be NAME:TYPE:FILE: {spec}",
                file=sys.stderr,
            )
            sys.exit(1)
        name, artifact_type, path = parts
        with open(path) as f:
            params[name] = {
                "artifact-type": artifact_type,
                "artifact": json.load(f),
            }

    for spec in args.text:
        if '=' not in spec:
            print(
                f"Error: text input must be NAME=VALUE: {spec}",
                file=sys.stderr,
            )
            sys.exit(1)
        name, value = spec.split('=', 1)
        params[name] = {
            "artifact-type": "TextBlobArtifact",
            "artifact": {"text": value},
        }

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
                },
            )
        finally:
            socket.close()

        if result.get("error"):
            err = result["error"]
            print(
                f"Error: [{err.get('type', '?')}] "
                f"{err.get('message', '?')}",
                file=sys.stderr,
            )
            sys.exit(1)

        artifacts = result.get("artifacts", {})

        if args.json:
            print(json.dumps(artifacts, indent=2))
        else:
            for name, entry in artifacts.items():
                artifact_type = entry.get("artifact-type", "?")
                artifact = entry.get("artifact", {})

                print(f"--- {name} ({artifact_type}) ---")
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

                print()

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
