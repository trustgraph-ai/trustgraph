"""
Connects to the graph query service and dumps all graph edges.
Uses streaming mode for lower time-to-first-result and reduced memory overhead.

Named graphs:
  - Default graph (empty): Core knowledge facts
  - urn:graph:source: Extraction provenance (document/chunk sources)
  - urn:graph:retrieval: Query-time explainability (question, exploration, focus, synthesis)
"""

import argparse
import os
from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_collection = 'default'
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")

# Named graph constants for convenience
GRAPH_DEFAULT = ""
GRAPH_SOURCE = "urn:graph:source"
GRAPH_RETRIEVAL = "urn:graph:retrieval"


def show_graph(url, flow_id, collection, limit, batch_size, graph=None, show_graph_column=False, token=None, workspace="default"):

    socket = Api(url, token=token, workspace=workspace).socket()
    flow = socket.flow(flow_id)

    try:
        for batch in flow.triples_query_stream(
            collection=collection,
            s=None, p=None, o=None,
            g=graph,  # Filter by named graph (None = all graphs)
            limit=limit,
            batch_size=batch_size,
        ):
            for triple in batch:
                s = triple.get("s", {})
                p = triple.get("p", {})
                o = triple.get("o", {})
                g = triple.get("g")  # Named graph (None = default graph)
                # Format terms for display
                s_str = s.get("v", s.get("i", str(s)))
                p_str = p.get("v", p.get("i", str(p)))
                o_str = o.get("v", o.get("i", str(o)))
                if show_graph_column:
                    g_str = g if g else "(default)"
                    print(f"[{g_str}]", s_str, p_str, o_str)
                else:
                    print(s_str, p_str, o_str)
    finally:
        socket.close()

def main():

    parser = argparse.ArgumentParser(
        prog='tg-show-graph',
        description=__doc__,
    )

    parser.add_argument(
        '-u', '--api-url',
        default=default_url,
        help=f'API URL (default: {default_url})',
    )

    parser.add_argument(
        '-f', '--flow-id',
        default="default",
        help=f'Flow ID (default: default)'
    )

    parser.add_argument(
        '-C', '--collection',
        default=default_collection,
        help=f'Collection ID (default: {default_collection})'
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
        '-l', '--limit',
        type=int,
        default=10000,
        help='Maximum number of triples to return (default: 10000)',
    )

    parser.add_argument(
        '-b', '--batch-size',
        type=int,
        default=20,
        help='Triples per streaming batch (default: 20)',
    )

    parser.add_argument(
        '-g', '--graph',
        default=None,
        help='Filter by named graph (e.g., urn:graph:source, urn:graph:retrieval). Use "" for default graph only.',
    )

    parser.add_argument(
        '--show-graph',
        action='store_true',
        help='Show graph column in output',
    )

    args = parser.parse_args()

    # Handle empty string for default graph filter
    graph = args.graph
    if graph == '""' or graph == "''":
        graph = ""  # Filter to default graph only

    try:

        show_graph(
            url = args.api_url,
            flow_id = args.flow_id,
            collection = args.collection,
            limit = args.limit,
            batch_size = args.batch_size,
            graph = graph,
            show_graph_column = args.show_graph,
            token = args.token,
            workspace=args.workspace,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()