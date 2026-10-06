"""
Lists available models from the text-completion backend
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
        prog='tg-list-models',
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
        '-j', '--json',
        action='store_true',
        help='Output as JSON',
    )

    args = parser.parse_args()

    try:

        api = Api(url=args.url, token=args.token, workspace=args.workspace)
        socket = api.socket()
        flow = socket.flow(args.flow_id)

        try:
            models = flow.list_models()
        finally:
            socket.close()

        if args.json:
            print(json.dumps(models, indent=2))
        else:
            if not models:
                print("No models available (or backend does not support listing).", file=sys.stderr)
                return

            for m in models:
                model_id = m.get('id', '?')
                parts = [model_id]

                name = m.get('name')
                if name:
                    parts.append(f"({name})")

                owner = m.get('owned_by')
                if owner:
                    parts.append(f"[{owner}]")

                ctx = m.get('context_length')
                if ctx:
                    parts.append(f"ctx={ctx}")

                max_out = m.get('max_output_length')
                if max_out:
                    parts.append(f"max_out={max_out}")

                family = m.get('family')
                if family:
                    parts.append(f"family={family}")

                param = m.get('parameter_size')
                if param:
                    parts.append(f"params={param}")

                quant = m.get('quantization')
                if quant:
                    parts.append(f"quant={quant}")

                print("  ".join(parts))

    except Exception as e:
        print("Exception:", e, flush=True)


if __name__ == "__main__":
    main()
