"""
Uses the GraphRAG service to answer a question
"""

import argparse
import os
import sys
from trustgraph.api import (
    Api,
    ExplainabilityClient,
    RAGChunk,
    ProvenanceEvent,
    Question,
    Grounding,
    Exploration,
    Focus,
    Synthesis,
)

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")
default_collection = 'default'
default_entity_limit = 50
default_triple_limit = 30
default_max_subgraph_size = 150
default_max_path_length = 2
default_edge_score_limit = 30
default_edge_limit = 25

def _question_explainable_api(
        url, flow_id, question_text, collection, entity_limit, triple_limit,
        max_subgraph_size, max_path_length, edge_score_limit=30,
        edge_limit=25, token=None, debug=False, workspace="default",
):
    """Execute graph RAG with explainability using the new API classes."""
    api = Api(url=url, token=token, workspace=workspace)
    socket = api.socket()
    flow = socket.flow(flow_id)
    explain_client = ExplainabilityClient(flow, retry_delay=0.2, max_retries=10)

    try:
        # Stream GraphRAG with explainability - process events as they arrive
        for item in flow.graph_rag_explain(
            query=question_text,
                        collection=collection,
            entity_limit=entity_limit,
            triple_limit=triple_limit,
            max_subgraph_size=max_subgraph_size,
            max_path_length=max_path_length,
            edge_score_limit=edge_score_limit,
            edge_limit=edge_limit,
        ):
            if isinstance(item, RAGChunk):
                # Print response content
                print(item.content, end="", flush=True)

            elif isinstance(item, ProvenanceEvent):
                # Use inline entity if available, otherwise fetch from graph
                prov_id = item.explain_id
                explain_graph = item.explain_graph or "urn:graph:retrieval"

                entity = item.entity
                if entity is None:
                    entity = explain_client.fetch_entity(
                        prov_id,
                        graph=explain_graph,
                                                collection=collection
                    )

                if entity is None:
                    if debug:
                        print(f"\n  [warning] Could not fetch entity: {prov_id}", file=sys.stderr)
                    continue

                # Display based on entity type
                if isinstance(entity, Question):
                    print(f"\n  [question] {prov_id}", file=sys.stderr)
                    if entity.query:
                        print(f"    Query: {entity.query}", file=sys.stderr)
                    if entity.timestamp:
                        print(f"    Time: {entity.timestamp}", file=sys.stderr)

                elif isinstance(entity, Grounding):
                    print(f"\n  [grounding] {prov_id}", file=sys.stderr)
                    if entity.concepts:
                        print(f"    Concepts: {len(entity.concepts)}", file=sys.stderr)
                        for concept in entity.concepts:
                            print(f"      - {concept}", file=sys.stderr)

                elif isinstance(entity, Exploration):
                    print(f"\n  [exploration] {prov_id}", file=sys.stderr)
                    if entity.edge_count:
                        print(f"    Edges explored: {entity.edge_count}", file=sys.stderr)
                    if entity.entities:
                        print(f"    Seed entities: {len(entity.entities)}", file=sys.stderr)
                        for ent in entity.entities:
                            label = explain_client.resolve_label(ent, collection)
                            print(f"      - {label}", file=sys.stderr)

                elif isinstance(entity, Focus):
                    print(f"\n  [focus] {prov_id}", file=sys.stderr)
                    if entity.selected_edge_uris:
                        print(f"    Focused on {len(entity.selected_edge_uris)} edge(s)", file=sys.stderr)

                    # Fetch full focus with edge details
                    focus_full = explain_client.fetch_focus_with_edges(
                        prov_id,
                        graph=explain_graph,
                                                collection=collection
                    )
                    if focus_full and focus_full.edge_selections:
                        for edge_sel in focus_full.edge_selections:
                            if edge_sel.edge:
                                # Resolve labels for edge components
                                s_label, p_label, o_label = explain_client.resolve_edge_labels(
                                    edge_sel.edge, collection
                                )
                                print(f"      Edge: ({s_label}, {p_label}, {o_label})", file=sys.stderr)
                            if edge_sel.reasoning:
                                r_short = edge_sel.reasoning[:100] + "..." if len(edge_sel.reasoning) > 100 else edge_sel.reasoning
                                print(f"        Reason: {r_short}", file=sys.stderr)

                elif isinstance(entity, Synthesis):
                    print(f"\n  [synthesis] {prov_id}", file=sys.stderr)
                    if entity.document:
                        print(f"    Document: {entity.document}", file=sys.stderr)

                else:
                    if debug:
                        print(f"\n  [unknown] {prov_id} (type: {entity.entity_type})", file=sys.stderr)

        print()  # Final newline

    finally:
        socket.close()


def question(
        url, flow_id, question, collection, entity_limit, triple_limit,
        max_subgraph_size, max_path_length, edge_score_limit=50,
        edge_limit=25, streaming=True, token=None,
        explainable=False, debug=False, show_usage=False,
        workspace="default",
):

    # Explainable mode uses the API to capture and process provenance events
    if explainable:
        _question_explainable_api(
            url=url,
            flow_id=flow_id,
            question_text=question,
                        collection=collection,
            entity_limit=entity_limit,
            triple_limit=triple_limit,
            max_subgraph_size=max_subgraph_size,
            max_path_length=max_path_length,
            edge_score_limit=edge_score_limit,
            edge_limit=edge_limit,
            token=token,
            debug=debug,
            workspace=workspace,
        )
        return

    # Create API client
    api = Api(url=url, token=token, workspace=workspace)

    if streaming:
        # Use socket client for streaming
        socket = api.socket()
        flow = socket.flow(flow_id)

        try:
            response = flow.graph_rag(
                query=question,
                                collection=collection,
                entity_limit=entity_limit,
                triple_limit=triple_limit,
                max_subgraph_size=max_subgraph_size,
                max_path_length=max_path_length,
                edge_score_limit=edge_score_limit,
                edge_limit=edge_limit,
                streaming=True
            )

            # Stream output
            last_chunk = None
            for chunk in response:
                print(chunk.content, end="", flush=True)
                last_chunk = chunk
            print()  # Final newline

            if show_usage and last_chunk:
                print(
                    f"Input tokens: {last_chunk.in_token}  "
                    f"Output tokens: {last_chunk.out_token}  "
                    f"Model: {last_chunk.model}",
                    file=sys.stderr,
                )

        finally:
            socket.close()
    else:
        # Use REST API for non-streaming
        flow = api.flow().id(flow_id)
        result = flow.graph_rag(
            query=question,
                        collection=collection,
            entity_limit=entity_limit,
            triple_limit=triple_limit,
            max_subgraph_size=max_subgraph_size,
            max_path_length=max_path_length,
            edge_score_limit=edge_score_limit,
            edge_limit=edge_limit,
        )
        print(result.text)

        if show_usage:
            print(
                f"Input tokens: {result.in_token}  "
                f"Output tokens: {result.out_token}  "
                f"Model: {result.model}",
                file=sys.stderr,
            )

def main():

    parser = argparse.ArgumentParser(
        prog='tg-invoke-graph-rag',
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
        help=f'Flow ID (default: default)'
    )

    parser.add_argument(
        '-q', '--question',
        required=True,
        help=f'Question to answer',
    )

    parser.add_argument(
        '-C', '--collection',
        default=default_collection,
        help=f'Collection ID (default: {default_collection})'
    )

    parser.add_argument(
        '-e', '--entity-limit',
        type=int,
        default=default_entity_limit,
        help=f'Entity limit (default: {default_entity_limit})'
    )

    parser.add_argument(
        '--triple-limit',
        type=int,
        default=default_triple_limit,
        help=f'Triple limit (default: {default_triple_limit})'
    )

    parser.add_argument(
        '-s', '--max-subgraph-size',
        type=int,
        default=default_max_subgraph_size,
        help=f'Max subgraph size (default: {default_max_subgraph_size})'
    )

    parser.add_argument(
        '-p', '--max-path-length',
        type=int,
        default=default_max_path_length,
        help=f'Max path length (default: {default_max_path_length})'
    )

    parser.add_argument(
        '--edge-score-limit',
        type=int,
        default=default_edge_score_limit,
        help=f'Semantic pre-filter limit before LLM scoring (default: {default_edge_score_limit})'
    )

    parser.add_argument(
        '--edge-limit',
        type=int,
        default=default_edge_limit,
        help=f'Max edges after LLM scoring (default: {default_edge_limit})'
    )

    parser.add_argument(
        '--no-streaming',
        action='store_true',
        help='Disable streaming (use non-streaming mode)'
    )

    parser.add_argument(
        '-x', '--explainable',
        action='store_true',
        help='Show provenance events: Question, Grounding, Exploration, Focus, Synthesis (implies streaming)'
    )

    parser.add_argument(
        '--debug',
        action='store_true',
        help='Show debug output for troubleshooting'
    )

    parser.add_argument(
        '--show-usage',
        action='store_true',
        help='Show token usage and model on stderr'
    )

    args = parser.parse_args()

    try:

        question(
            url=args.url,
            flow_id=args.flow_id,
            question=args.question,
            collection=args.collection,
            entity_limit=args.entity_limit,
            triple_limit=args.triple_limit,
            max_subgraph_size=args.max_subgraph_size,
            max_path_length=args.max_path_length,
            edge_score_limit=args.edge_score_limit,
            edge_limit=args.edge_limit,
            streaming=not args.no_streaming,
            token=args.token,
            explainable=args.explainable,
            debug=args.debug,
            show_usage=args.show_usage,
            workspace=args.workspace,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()
