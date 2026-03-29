"""
List all explainability sessions (GraphRAG and Agent) in a collection.

Queries for all questions stored in the retrieval graph and displays them
with their session IDs, type (GraphRAG or Agent), and timestamps.

Examples:
  tg-list-explain-traces -U trustgraph -C default
  tg-list-explain-traces --limit 20 --format json
"""

import argparse
import json
import os
import sys
from tabulate import tabulate
from trustgraph.api import Api, ExplainabilityClient

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_user = 'trustgraph'
default_collection = 'default'

# Retrieval graph
RETRIEVAL_GRAPH = "urn:graph:retrieval"


def truncate_text(text, max_len=60):
    """Truncate text to max length with ellipsis."""
    if not text:
        return ""
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + "..."


def print_table(sessions):
    """Print sessions as a table."""
    if not sessions:
        print("No explainability sessions found.")
        return

    rows = []
    for session in sessions:
        rows.append([
            session["id"],
            session.get("type", "Unknown"),
            truncate_text(session["question"], 45),
            session.get("time", "")
        ])

    headers = ["Session ID", "Type", "Question", "Time"]
    print(tabulate(rows, headers=headers, tablefmt="simple"))


def print_json(sessions):
    """Print sessions as JSON."""
    print(json.dumps(sessions, indent=2))


# Map type names for display
TYPE_DISPLAY = {
    "graphrag": "GraphRAG",
    "docrag": "DocRAG",
    "agent": "Agent",
}


def main():
    parser = argparse.ArgumentParser(
        prog='tg-list-explain-traces',
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        '-u', '--api-url',
        default=default_url,
        help=f'API URL (default: {default_url})',
    )

    parser.add_argument(
        '-t', '--token',
        default=default_token,
        help='Auth token (default: $TRUSTGRAPH_TOKEN)',
    )

    parser.add_argument(
        '-U', '--user',
        default=default_user,
        help=f'User ID (default: {default_user})',
    )

    parser.add_argument(
        '-C', '--collection',
        default=default_collection,
        help=f'Collection (default: {default_collection})',
    )

    parser.add_argument(
        '-f', '--flow-id',
        default='default',
        help='Flow ID (default: default)',
    )

    parser.add_argument(
        '--limit',
        type=int,
        default=50,
        help='Max results (default: 50)',
    )

    parser.add_argument(
        '--format',
        choices=['table', 'json'],
        default='table',
        help='Output format: table (default), json',
    )

    args = parser.parse_args()

    try:
        api = Api(args.api_url, token=args.token)
        socket = api.socket()
        flow = socket.flow(args.flow_id)
        explain_client = ExplainabilityClient(flow)

        try:
            # List all sessions — uses persistent websocket via SocketClient
            questions = explain_client.list_sessions(
                graph=RETRIEVAL_GRAPH,
                user=args.user,
                collection=args.collection,
                limit=args.limit,
            )

            # detect_session_type is mostly a fast URI pattern check,
            # only falls back to network calls for unrecognised URIs
            sessions = []
            for q in questions:
                session_type = explain_client.detect_session_type(
                    q.uri,
                    graph=RETRIEVAL_GRAPH,
                    user=args.user,
                    collection=args.collection
                )

                sessions.append({
                    "id": q.uri,
                    "type": TYPE_DISPLAY.get(session_type, session_type.title()),
                    "question": q.query,
                    "time": q.timestamp,
                })

            if args.format == 'json':
                print_json(sessions)
            else:
                print_table(sessions)

        finally:
            socket.close()

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
