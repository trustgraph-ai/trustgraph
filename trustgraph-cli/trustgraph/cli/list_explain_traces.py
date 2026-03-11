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
from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_user = 'trustgraph'
default_collection = 'default'

# Predicates
TG = "https://trustgraph.ai/ns/"
TG_QUERY = TG + "query"
TG_AGENT_SESSION = TG + "AgentSession"
PROV = "http://www.w3.org/ns/prov#"
PROV_STARTED_AT_TIME = PROV + "startedAtTime"
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"

# Retrieval graph
RETRIEVAL_GRAPH = "urn:graph:retrieval"


def query_triples(socket, flow_id, user, collection, s=None, p=None, o=None, g=None, limit=1000):
    """Query triples using the socket API."""
    request = {
        "user": user,
        "collection": collection,
        "limit": limit,
        "streaming": False,
    }

    if s is not None:
        request["s"] = {"t": "i", "i": s}
    if p is not None:
        request["p"] = {"t": "i", "i": p}
    if o is not None:
        if isinstance(o, str):
            if o.startswith("http://") or o.startswith("https://") or o.startswith("urn:"):
                request["o"] = {"t": "i", "i": o}
            else:
                request["o"] = {"t": "l", "v": o}
        elif isinstance(o, dict):
            request["o"] = o
    if g is not None:
        request["g"] = g

    triples = []
    try:
        for response in socket._send_request_sync("triples", flow_id, request, streaming_raw=True):
            if isinstance(response, dict):
                triple_list = response.get("response", response.get("triples", []))
            else:
                triple_list = response

            if not isinstance(triple_list, list):
                triple_list = [triple_list] if triple_list else []

            for t in triple_list:
                s_val = extract_value(t.get("s", {}))
                p_val = extract_value(t.get("p", {}))
                o_val = extract_value(t.get("o", {}))
                triples.append((s_val, p_val, o_val))
    except Exception as e:
        print(f"Error querying triples: {e}", file=sys.stderr)

    return triples


def extract_value(term):
    """Extract value from a term dict."""
    if not term:
        return ""

    t = term.get("t") or term.get("type")

    if t == "i":
        return term.get("i") or term.get("iri", "")
    elif t == "l":
        return term.get("v") or term.get("value", "")
    elif t == "t":
        # Quoted triple
        tr = term.get("tr") or term.get("triple", {})
        return {
            "s": extract_value(tr.get("s", {})),
            "p": extract_value(tr.get("p", {})),
            "o": extract_value(tr.get("o", {})),
        }

    # Fallback for raw values
    if "i" in term:
        return term["i"]
    if "v" in term:
        return term["v"]

    return str(term)


def get_timestamp(socket, flow_id, user, collection, question_id):
    """Get timestamp for a question."""
    triples = query_triples(
        socket, flow_id, user, collection,
        s=question_id, p=PROV_STARTED_AT_TIME, g=RETRIEVAL_GRAPH
    )
    for s, p, o in triples:
        return o
    return ""


def get_session_type(socket, flow_id, user, collection, session_id):
    """Get the type of session (Agent or GraphRAG)."""
    triples = query_triples(
        socket, flow_id, user, collection,
        s=session_id, p=RDF_TYPE, g=RETRIEVAL_GRAPH
    )
    for s, p, o in triples:
        if o == TG_AGENT_SESSION:
            return "Agent"
    return "GraphRAG"


def list_sessions(socket, flow_id, user, collection, limit):
    """List all explainability sessions (GraphRAG and Agent) by finding questions."""
    # Query for all triples with predicate = tg:query
    triples = query_triples(
        socket, flow_id, user, collection,
        p=TG_QUERY, g=RETRIEVAL_GRAPH, limit=limit
    )

    sessions = []
    for question_id, _, query_text in triples:
        # Get timestamp if available
        timestamp = get_timestamp(socket, flow_id, user, collection, question_id)
        # Get session type (Agent or GraphRAG)
        session_type = get_session_type(socket, flow_id, user, collection, question_id)

        sessions.append({
            "id": question_id,
            "type": session_type,
            "question": query_text,
            "time": timestamp,
        })

    # Sort by timestamp (newest first) if available
    sessions.sort(key=lambda x: x.get("time", ""), reverse=True)

    return sessions


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

        try:
            sessions = list_sessions(
                socket=socket,
                flow_id=args.flow_id,
                user=args.user,
                collection=args.collection,
                limit=args.limit,
            )

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
