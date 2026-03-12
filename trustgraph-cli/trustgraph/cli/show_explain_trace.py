"""
Show full explainability trace for a GraphRAG or Agent session.

Given a question/session URI, displays the complete trace:
- GraphRAG: Question -> Exploration -> Focus (edge selection) -> Synthesis (answer)
- Agent: Session -> Iteration(s) (thought/action/observation) -> Final Answer

The tool auto-detects the trace type based on rdf:type.

Examples:
  tg-show-explain-trace -U trustgraph -C default "urn:trustgraph:question:abc123"
  tg-show-explain-trace -U trustgraph -C default "urn:trustgraph:agent:abc123"
  tg-show-explain-trace --max-answer 1000 "urn:trustgraph:question:abc123"
  tg-show-explain-trace --show-provenance "urn:trustgraph:question:abc123"
"""

import argparse
import json
import os
import sys
from trustgraph.api import (
    Api,
    ExplainabilityClient,
    Question,
    Exploration,
    Focus,
    Synthesis,
    Analysis,
    Conclusion,
)

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_user = 'trustgraph'
default_collection = 'default'

# Graphs
RETRIEVAL_GRAPH = "urn:graph:retrieval"
SOURCE_GRAPH = "urn:graph:source"

# Provenance predicates for edge tracing
TG = "https://trustgraph.ai/ns/"
TG_REIFIES = TG + "reifies"
PROV = "http://www.w3.org/ns/prov#"
PROV_WAS_DERIVED_FROM = PROV + "wasDerivedFrom"


def trace_edge_provenance(flow, user, collection, edge, label_cache, explain_client):
    """
    Trace an edge back to its source document via reification.

    Args:
        flow: SocketFlowInstance
        user: User identifier
        collection: Collection identifier
        edge: Dict with s, p, o keys
        label_cache: Dict for caching labels
        explain_client: ExplainabilityClient for label resolution

    Returns:
        List of provenance chains, each chain is list of {uri, label}
    """
    edge_s = edge.get("s", "")
    edge_p = edge.get("p", "")
    edge_o = edge.get("o", "")

    # Build quoted triple for lookup
    def build_term(val):
        if isinstance(val, str) and (val.startswith("http") or val.startswith("urn:")):
            return {"t": "i", "i": val}
        return {"t": "l", "v": str(val)}

    quoted_triple = {
        "t": "t",
        "tr": {
            "s": build_term(edge_s),
            "p": build_term(edge_p),
            "o": build_term(edge_o),
        }
    }

    # Query: ?stmt tg:reifies <<edge>>
    try:
        results = flow.triples_query(
            p=TG_REIFIES,
            o=quoted_triple,
            g=SOURCE_GRAPH,
            user=user,
            collection=collection,
            limit=10
        )
    except Exception:
        return []

    # Extract statement URIs
    stmt_uris = []
    for t in results:
        s_term = t.get("s", {})
        s_val = s_term.get("i") or s_term.get("v", "")
        if s_val:
            stmt_uris.append(s_val)

    # For each statement, trace wasDerivedFrom chain
    provenance_chains = []
    for stmt_uri in stmt_uris:
        chain = trace_provenance_chain(flow, user, collection, stmt_uri, label_cache, explain_client)
        if chain:
            provenance_chains.append(chain)

    return provenance_chains


def trace_provenance_chain(flow, user, collection, start_uri, label_cache, explain_client, max_depth=10):
    """Trace prov:wasDerivedFrom chain from start_uri to root."""
    chain = []
    current = start_uri

    for _ in range(max_depth):
        if not current:
            break

        # Get label
        if current in label_cache:
            label = label_cache[current]
        else:
            label = explain_client.resolve_label(current, user, collection)
            label_cache[current] = label

        chain.append({"uri": current, "label": label})

        # Get parent via wasDerivedFrom
        try:
            results = flow.triples_query(
                s=current,
                p=PROV_WAS_DERIVED_FROM,
                g=SOURCE_GRAPH,
                user=user,
                collection=collection,
                limit=1
            )
        except Exception:
            break

        parent = None
        for t in results:
            o_term = t.get("o", {})
            parent = o_term.get("i") or o_term.get("v", "")
            break

        if not parent or parent == current:
            break
        current = parent

    return chain


def format_provenance_chain(chain):
    """Format a provenance chain for display."""
    if not chain:
        return ""
    labels = [item.get("label", item.get("uri", "?")) for item in chain]
    return " -> ".join(labels)


def print_graphrag_text(trace, explain_client, flow, user, collection, show_provenance=False):
    """Print GraphRAG trace in text format."""
    question = trace.get("question")

    print(f"=== GraphRAG Session: {question.uri if question else 'Unknown'} ===")
    print()

    if question:
        print(f"Question: {question.query}")
        if question.timestamp:
            print(f"Time: {question.timestamp}")
    print()

    # Exploration
    print("--- Exploration ---")
    exploration = trace.get("exploration")
    if exploration:
        print(f"Retrieved {exploration.edge_count} edges from knowledge graph")
    else:
        print("No exploration data found")
    print()

    # Focus
    print("--- Focus (Edge Selection) ---")
    focus = trace.get("focus")
    if focus:
        edges = focus.edge_selections
        print(f"Selected {len(edges)} edges:")
        print()

        label_cache = {}

        for i, edge_sel in enumerate(edges, 1):
            if edge_sel.edge:
                s_label, p_label, o_label = explain_client.resolve_edge_labels(
                    edge_sel.edge, user, collection
                )
                print(f"  {i}. ({s_label}, {p_label}, {o_label})")

            if edge_sel.reasoning:
                r_short = edge_sel.reasoning[:100] + "..." if len(edge_sel.reasoning) > 100 else edge_sel.reasoning
                print(f"     Reasoning: {r_short}")

            if show_provenance and edge_sel.edge:
                provenance = trace_edge_provenance(
                    flow, user, collection, edge_sel.edge,
                    label_cache, explain_client
                )
                for chain in provenance:
                    chain_str = format_provenance_chain(chain)
                    if chain_str:
                        print(f"     Source: {chain_str}")

            print()
    else:
        print("No focus data found")
        print()

    # Synthesis
    print("--- Synthesis ---")
    synthesis = trace.get("synthesis")
    if synthesis:
        if synthesis.content:
            print("Answer:")
            for line in synthesis.content.split("\n"):
                print(f"  {line}")
        else:
            print("No answer content found")
    else:
        print("No synthesis data found")


def print_docrag_text(trace):
    """Print DocRAG trace in text format."""
    question = trace.get("question")

    print(f"=== DocRAG Session: {question.uri if question else 'Unknown'} ===")
    print()

    if question:
        print(f"Question: {question.query}")
        if question.timestamp:
            print(f"Time: {question.timestamp}")
    print()

    # Exploration
    print("--- Exploration ---")
    exploration = trace.get("exploration")
    if exploration:
        print(f"Retrieved {exploration.chunk_count} chunks from document store")
    else:
        print("No exploration data found")
    print()

    # Synthesis (no Focus step for DocRAG)
    print("--- Synthesis ---")
    synthesis = trace.get("synthesis")
    if synthesis:
        if synthesis.content:
            print("Answer:")
            for line in synthesis.content.split("\n"):
                print(f"  {line}")
        else:
            print("No answer content found")
    else:
        print("No synthesis data found")


def print_agent_text(trace):
    """Print Agent trace in text format."""
    question = trace.get("question")

    print(f"=== Agent Session: {question.uri if question else 'Unknown'} ===")
    print()

    if question:
        print(f"Question: {question.query}")
        if question.timestamp:
            print(f"Time: {question.timestamp}")
    print()

    # Analysis steps
    print("--- Analysis ---")
    iterations = trace.get("iterations", [])
    if iterations:
        for i, analysis in enumerate(iterations, 1):
            print(f"Analysis {i}:")
            print(f"  Thought: {analysis.thought or 'N/A'}")
            print(f"  Action: {analysis.action or 'N/A'}")

            if analysis.arguments:
                # Try to pretty-print JSON arguments
                try:
                    args_obj = json.loads(analysis.arguments)
                    args_str = json.dumps(args_obj, indent=4)
                    print(f"  Arguments:")
                    for line in args_str.split('\n'):
                        print(f"    {line}")
                except Exception:
                    print(f"  Arguments: {analysis.arguments}")
            else:
                print(f"  Arguments: N/A")

            obs = analysis.observation or 'N/A'
            if obs and len(obs) > 200:
                obs = obs[:200] + "... [truncated]"
            print(f"  Observation: {obs}")
            print()
    else:
        print("No analysis steps recorded")
        print()

    # Conclusion
    print("--- Conclusion ---")
    conclusion = trace.get("conclusion")
    if conclusion and conclusion.answer:
        print("Answer:")
        for line in conclusion.answer.split("\n"):
            print(f"  {line}")
    else:
        print("No conclusion recorded")


def trace_to_dict(trace, trace_type):
    """Convert trace entities to JSON-serializable dict."""
    if trace_type == "agent":
        question = trace.get("question")
        return {
            "type": "agent",
            "session_id": question.uri if question else None,
            "question": question.query if question else None,
            "time": question.timestamp if question else None,
            "iterations": [
                {
                    "id": a.uri,
                    "thought": a.thought,
                    "action": a.action,
                    "arguments": a.arguments,
                    "observation": a.observation,
                }
                for a in trace.get("iterations", [])
            ],
            "conclusion": {
                "id": trace["conclusion"].uri,
                "answer": trace["conclusion"].answer,
            } if trace.get("conclusion") else None,
        }
    elif trace_type == "docrag":
        question = trace.get("question")
        exploration = trace.get("exploration")
        synthesis = trace.get("synthesis")

        return {
            "type": "docrag",
            "question_id": question.uri if question else None,
            "question": question.query if question else None,
            "time": question.timestamp if question else None,
            "exploration": {
                "id": exploration.uri,
                "chunk_count": exploration.chunk_count,
            } if exploration else None,
            "synthesis": {
                "id": synthesis.uri,
                "document_uri": synthesis.document_uri,
                "answer": synthesis.content,
            } if synthesis else None,
        }
    else:
        # graphrag
        question = trace.get("question")
        exploration = trace.get("exploration")
        focus = trace.get("focus")
        synthesis = trace.get("synthesis")

        return {
            "type": "graphrag",
            "question_id": question.uri if question else None,
            "question": question.query if question else None,
            "time": question.timestamp if question else None,
            "exploration": {
                "id": exploration.uri,
                "edge_count": exploration.edge_count,
            } if exploration else None,
            "focus": {
                "id": focus.uri,
                "selected_edges": [
                    {
                        "edge": edge_sel.edge,
                        "reasoning": edge_sel.reasoning,
                    }
                    for edge_sel in focus.edge_selections
                ],
            } if focus else None,
            "synthesis": {
                "id": synthesis.uri,
                "document_uri": synthesis.document_uri,
                "answer": synthesis.content,
            } if synthesis else None,
        }


def main():
    parser = argparse.ArgumentParser(
        prog='tg-show-explain-trace',
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        'question_id',
        help='Question/session URI to show trace for',
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
        '--max-answer',
        type=int,
        default=500,
        help='Max chars for answer display (default: 500)',
    )

    parser.add_argument(
        '--show-provenance',
        action='store_true',
        help='Also trace edges back to source documents',
    )

    parser.add_argument(
        '--format',
        choices=['text', 'json'],
        default='text',
        help='Output format: text (default), json',
    )

    args = parser.parse_args()

    try:
        api = Api(args.api_url, token=args.token)
        socket = api.socket()
        flow = socket.flow(args.flow_id)
        explain_client = ExplainabilityClient(flow)

        try:
            # Detect trace type
            trace_type = explain_client.detect_session_type(
                args.question_id,
                graph=RETRIEVAL_GRAPH,
                user=args.user,
                collection=args.collection,
            )

            if trace_type == "agent":
                # Fetch and display agent trace
                trace = explain_client.fetch_agent_trace(
                    args.question_id,
                    graph=RETRIEVAL_GRAPH,
                    user=args.user,
                    collection=args.collection,
                    api=api,
                    max_content=args.max_answer,
                )

                if args.format == 'json':
                    print(json.dumps(trace_to_dict(trace, "agent"), indent=2))
                else:
                    print_agent_text(trace)

            elif trace_type == "docrag":
                # Fetch and display DocRAG trace
                trace = explain_client.fetch_docrag_trace(
                    args.question_id,
                    graph=RETRIEVAL_GRAPH,
                    user=args.user,
                    collection=args.collection,
                    api=api,
                    max_content=args.max_answer,
                )

                if args.format == 'json':
                    print(json.dumps(trace_to_dict(trace, "docrag"), indent=2))
                else:
                    print_docrag_text(trace)

            else:
                # Fetch and display GraphRAG trace
                trace = explain_client.fetch_graphrag_trace(
                    args.question_id,
                    graph=RETRIEVAL_GRAPH,
                    user=args.user,
                    collection=args.collection,
                    api=api,
                    max_content=args.max_answer,
                )

                if args.format == 'json':
                    print(json.dumps(trace_to_dict(trace, "graphrag"), indent=2))
                else:
                    print_graphrag_text(
                        trace, explain_client, flow,
                        args.user, args.collection,
                        show_provenance=args.show_provenance
                    )

        finally:
            socket.close()

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
