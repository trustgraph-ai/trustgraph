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
from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_user = 'trustgraph'
default_collection = 'default'

# Predicates
TG = "https://trustgraph.ai/ns/"
TG_QUERY = TG + "query"
TG_EDGE_COUNT = TG + "edgeCount"
TG_SELECTED_EDGE = TG + "selectedEdge"
TG_EDGE = TG + "edge"
TG_REASONING = TG + "reasoning"
TG_CONTENT = TG + "content"
TG_DOCUMENT = TG + "document"
TG_REIFIES = TG + "reifies"
# Agent predicates
TG_THOUGHT = TG + "thought"
TG_ACTION = TG + "action"
TG_ARGUMENTS = TG + "arguments"
TG_OBSERVATION = TG + "observation"
TG_ANSWER = TG + "answer"
TG_AGENT_SESSION = TG + "AgentSession"
TG_AGENT_ITERATION = TG + "AgentIteration"
TG_AGENT_FINAL = TG + "AgentFinal"
PROV = "http://www.w3.org/ns/prov#"
PROV_STARTED_AT_TIME = PROV + "startedAtTime"
PROV_WAS_DERIVED_FROM = PROV + "wasDerivedFrom"
PROV_WAS_GENERATED_BY = PROV + "wasGeneratedBy"
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"

# Graphs
RETRIEVAL_GRAPH = "urn:graph:retrieval"
SOURCE_GRAPH = "urn:graph:source"


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


def get_node_properties(socket, flow_id, user, collection, node_uri, graph=RETRIEVAL_GRAPH):
    """Get all properties of a node as a dict."""
    triples = query_triples(socket, flow_id, user, collection, s=node_uri, g=graph)
    props = {}
    for s, p, o in triples:
        if p not in props:
            props[p] = []
        props[p].append(o)
    return props


def find_by_predicate_object(socket, flow_id, user, collection, predicate, obj, graph=RETRIEVAL_GRAPH):
    """Find subjects where predicate = obj."""
    triples = query_triples(socket, flow_id, user, collection, p=predicate, o=obj, g=graph)
    return [s for s, p, o in triples]


def get_label(socket, flow_id, user, collection, uri, label_cache):
    """Get label for a URI, with caching."""
    if not isinstance(uri, str) or not (uri.startswith("http://") or uri.startswith("https://") or uri.startswith("urn:")):
        return uri

    if uri in label_cache:
        return label_cache[uri]

    triples = query_triples(socket, flow_id, user, collection, s=uri, p=RDFS_LABEL)
    for s, p, o in triples:
        label_cache[uri] = o
        return o

    label_cache[uri] = uri
    return uri


def get_document_content(api, user, doc_id, max_content):
    """Fetch document content from librarian API."""
    try:
        library = api.library()
        content = library.get_document_content(user=user, id=doc_id)

        # Try to decode as text
        try:
            text = content.decode('utf-8')
            if len(text) > max_content:
                return text[:max_content] + "... [truncated]"
            return text
        except UnicodeDecodeError:
            return f"[Binary: {len(content)} bytes]"
    except Exception as e:
        return f"[Error fetching content: {e}]"


def trace_edge_provenance(socket, flow_id, user, collection, edge_s, edge_p, edge_o, label_cache):
    """Trace an edge back to its source document via reification."""
    # Build the quoted triple for lookup
    quoted_triple = {
        "t": "t",
        "tr": {
            "s": {"t": "i", "i": edge_s} if isinstance(edge_s, str) and (edge_s.startswith("http") or edge_s.startswith("urn:")) else {"t": "l", "v": edge_s},
            "p": {"t": "i", "i": edge_p},
            "o": {"t": "i", "i": edge_o} if isinstance(edge_o, str) and (edge_o.startswith("http") or edge_o.startswith("urn:")) else {"t": "l", "v": edge_o},
        }
    }

    # Query: ?stmt tg:reifies <<edge>>
    request = {
        "user": user,
        "collection": collection,
        "limit": 10,
        "streaming": False,
        "p": {"t": "i", "i": TG_REIFIES},
        "o": quoted_triple,
        "g": SOURCE_GRAPH,
    }

    stmt_uris = []
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
                if s_val:
                    stmt_uris.append(s_val)
    except Exception:
        pass

    # For each statement, find wasDerivedFrom chain
    provenance_chains = []
    for stmt_uri in stmt_uris:
        chain = trace_provenance_chain(socket, flow_id, user, collection, stmt_uri, label_cache)
        if chain:
            provenance_chains.append(chain)

    return provenance_chains


def trace_provenance_chain(socket, flow_id, user, collection, start_uri, label_cache, max_depth=10):
    """Trace prov:wasDerivedFrom chain from start_uri to root."""
    chain = []
    current = start_uri

    for _ in range(max_depth):
        if not current:
            break

        label = get_label(socket, flow_id, user, collection, current, label_cache)
        chain.append({"uri": current, "label": label})

        # Get parent
        triples = query_triples(
            socket, flow_id, user, collection,
            s=current, p=PROV_WAS_DERIVED_FROM, g=SOURCE_GRAPH
        )
        parent = None
        for s, p, o in triples:
            parent = o
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


def format_edge(edge, label_cache=None, socket=None, flow_id=None, user=None, collection=None):
    """Format a quoted triple edge for display."""
    if not isinstance(edge, dict):
        return str(edge)

    s = edge.get("s", "?")
    p = edge.get("p", "?")
    o = edge.get("o", "?")

    # Get labels if available
    if label_cache and socket:
        s_label = get_label(socket, flow_id, user, collection, s, label_cache)
        p_label = get_label(socket, flow_id, user, collection, p, label_cache)
        o_label = get_label(socket, flow_id, user, collection, o, label_cache)
    else:
        # Shorten URIs for display
        s_label = s.split("/")[-1] if "/" in str(s) else s
        p_label = p.split("/")[-1] if "/" in str(p) else p
        o_label = o.split("/")[-1] if "/" in str(o) else o

    return f"({s_label}, {p_label}, {o_label})"


def detect_trace_type(socket, flow_id, user, collection, entity_id):
    """
    Detect whether an entity is an agent session or GraphRAG question.

    Returns:
        "agent" if entity has rdf:type = tg:AgentSession
        "graphrag" otherwise (default)
    """
    triples = query_triples(
        socket, flow_id, user, collection,
        s=entity_id, p=RDF_TYPE, g=RETRIEVAL_GRAPH
    )
    for s, p, o in triples:
        if o == TG_AGENT_SESSION:
            return "agent"
    return "graphrag"


def build_agent_trace(socket, flow_id, user, collection, session_id, api=None, max_answer=500):
    """Build the full explainability trace for an agent session."""
    trace = {
        "session_id": session_id,
        "type": "agent",
        "question": None,
        "time": None,
        "iterations": [],
        "final_answer": None,
    }

    # Get session metadata
    props = get_node_properties(socket, flow_id, user, collection, session_id)
    trace["question"] = props.get(TG_QUERY, [None])[0]
    trace["time"] = props.get(PROV_STARTED_AT_TIME, [None])[0]

    # Find all entities derived from this session (iterations and final)
    # Start by looking for entities where prov:wasDerivedFrom = session_id
    current_uri = session_id
    iteration_num = 1

    while True:
        # Find entities derived from current
        derived_ids = find_by_predicate_object(
            socket, flow_id, user, collection,
            PROV_WAS_DERIVED_FROM, current_uri
        )

        if not derived_ids:
            break

        derived_id = derived_ids[0]
        derived_props = get_node_properties(socket, flow_id, user, collection, derived_id)

        # Check type
        types = derived_props.get(RDF_TYPE, [])

        if TG_AGENT_ITERATION in types:
            iteration = {
                "id": derived_id,
                "iteration_num": iteration_num,
                "thought": derived_props.get(TG_THOUGHT, [None])[0],
                "action": derived_props.get(TG_ACTION, [None])[0],
                "arguments": derived_props.get(TG_ARGUMENTS, [None])[0],
                "observation": derived_props.get(TG_OBSERVATION, [None])[0],
            }
            trace["iterations"].append(iteration)
            current_uri = derived_id
            iteration_num += 1

        elif TG_AGENT_FINAL in types:
            answer = derived_props.get(TG_ANSWER, [None])[0]
            if answer and len(answer) > max_answer:
                answer = answer[:max_answer] + "... [truncated]"
            trace["final_answer"] = {
                "id": derived_id,
                "answer": answer,
            }
            break

        else:
            # Unknown type, stop traversal
            break

    return trace


def print_agent_text(trace):
    """Print agent trace in text format."""
    print(f"=== Agent Session: {trace['session_id']} ===")
    print()

    if trace["question"]:
        print(f"Question: {trace['question']}")
    if trace["time"]:
        print(f"Time: {trace['time']}")
    print()

    # Iterations
    print("--- Iterations ---")
    iterations = trace.get("iterations", [])
    if iterations:
        for iteration in iterations:
            print(f"Iteration {iteration['iteration_num']}:")
            print(f"  Thought: {iteration.get('thought', 'N/A')}")
            print(f"  Action: {iteration.get('action', 'N/A')}")

            args = iteration.get('arguments')
            if args:
                # Try to pretty-print JSON arguments
                try:
                    import json
                    args_obj = json.loads(args)
                    args_str = json.dumps(args_obj, indent=4)
                    # Indent each line
                    args_lines = args_str.split('\n')
                    print(f"  Arguments:")
                    for line in args_lines:
                        print(f"    {line}")
                except:
                    print(f"  Arguments: {args}")
            else:
                print(f"  Arguments: N/A")

            obs = iteration.get('observation', 'N/A')
            if obs and len(obs) > 200:
                obs = obs[:200] + "... [truncated]"
            print(f"  Observation: {obs}")
            print()
    else:
        print("No iterations recorded")
        print()

    # Final answer
    print("--- Final Answer ---")
    final = trace.get("final_answer")
    if final and final.get("answer"):
        print("Answer:")
        for line in final["answer"].split("\n"):
            print(f"  {line}")
    else:
        print("No final answer recorded")


def print_agent_json(trace):
    """Print agent trace as JSON."""
    print(json.dumps(trace, indent=2))


def build_trace(socket, flow_id, user, collection, question_id, api=None, show_provenance=False, max_answer=500):
    """Build the full explainability trace for a question."""
    label_cache = {}

    trace = {
        "question_id": question_id,
        "question": None,
        "time": None,
        "exploration": None,
        "focus": None,
        "synthesis": None,
    }

    # Get question metadata
    props = get_node_properties(socket, flow_id, user, collection, question_id)
    trace["question"] = props.get(TG_QUERY, [None])[0]
    trace["time"] = props.get(PROV_STARTED_AT_TIME, [None])[0]

    # Find exploration: ?exploration prov:wasGeneratedBy question_id
    exploration_ids = find_by_predicate_object(
        socket, flow_id, user, collection,
        PROV_WAS_GENERATED_BY, question_id
    )

    if exploration_ids:
        exploration_id = exploration_ids[0]
        exploration_props = get_node_properties(socket, flow_id, user, collection, exploration_id)
        trace["exploration"] = {
            "id": exploration_id,
            "edge_count": exploration_props.get(TG_EDGE_COUNT, [None])[0],
        }

        # Find focus: ?focus prov:wasDerivedFrom exploration_id
        focus_ids = find_by_predicate_object(
            socket, flow_id, user, collection,
            PROV_WAS_DERIVED_FROM, exploration_id
        )

        if focus_ids:
            focus_id = focus_ids[0]
            focus_props = get_node_properties(socket, flow_id, user, collection, focus_id)

            # Get selected edges
            edge_selection_uris = focus_props.get(TG_SELECTED_EDGE, [])
            selected_edges = []

            for edge_sel_uri in edge_selection_uris:
                edge_sel_props = get_node_properties(socket, flow_id, user, collection, edge_sel_uri)
                edge = edge_sel_props.get(TG_EDGE, [None])[0]
                reasoning = edge_sel_props.get(TG_REASONING, [None])[0]

                edge_info = {
                    "edge": edge,
                    "reasoning": reasoning,
                }

                # Trace provenance if requested
                if show_provenance and isinstance(edge, dict):
                    provenance = trace_edge_provenance(
                        socket, flow_id, user, collection,
                        edge.get("s", ""), edge.get("p", ""), edge.get("o", ""),
                        label_cache
                    )
                    edge_info["provenance"] = provenance

                selected_edges.append(edge_info)

            trace["focus"] = {
                "id": focus_id,
                "selected_edges": selected_edges,
            }

            # Find synthesis: ?synthesis prov:wasDerivedFrom focus_id
            synthesis_ids = find_by_predicate_object(
                socket, flow_id, user, collection,
                PROV_WAS_DERIVED_FROM, focus_id
            )

            if synthesis_ids:
                synthesis_id = synthesis_ids[0]
                synthesis_props = get_node_properties(socket, flow_id, user, collection, synthesis_id)

                # Get content directly or via document reference
                content = synthesis_props.get(TG_CONTENT, [None])[0]
                doc_id = synthesis_props.get(TG_DOCUMENT, [None])[0]

                if not content and doc_id and api:
                    content = get_document_content(api, user, doc_id, max_answer)
                elif content and len(content) > max_answer:
                    content = content[:max_answer] + "... [truncated]"

                trace["synthesis"] = {
                    "id": synthesis_id,
                    "document_id": doc_id,
                    "answer": content,
                }

    # Store label cache for formatting
    trace["_label_cache"] = label_cache

    return trace


def print_text(trace, show_provenance=False):
    """Print trace in text format."""
    label_cache = trace.get("_label_cache", {})

    print(f"=== GraphRAG Session: {trace['question_id']} ===")
    print()

    if trace["question"]:
        print(f"Question: {trace['question']}")
    if trace["time"]:
        print(f"Time: {trace['time']}")
    print()

    # Exploration
    print("--- Exploration ---")
    exploration = trace.get("exploration")
    if exploration:
        edge_count = exploration.get("edge_count", "?")
        print(f"Retrieved {edge_count} edges from knowledge graph")
    else:
        print("No exploration data found")
    print()

    # Focus
    print("--- Focus (Edge Selection) ---")
    focus = trace.get("focus")
    if focus:
        edges = focus.get("selected_edges", [])
        print(f"Selected {len(edges)} edges:")
        print()

        for i, edge_info in enumerate(edges, 1):
            edge = edge_info.get("edge")
            reasoning = edge_info.get("reasoning")

            if edge:
                edge_str = format_edge(edge)
                print(f"  {i}. {edge_str}")

            if reasoning:
                r_short = reasoning[:100] + "..." if len(reasoning) > 100 else reasoning
                print(f"     Reasoning: {r_short}")

            if show_provenance:
                provenance = edge_info.get("provenance", [])
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
        answer = synthesis.get("answer")
        if answer:
            print("Answer:")
            # Indent the answer
            for line in answer.split("\n"):
                print(f"  {line}")
        else:
            print("No answer content found")
    else:
        print("No synthesis data found")


def print_json(trace):
    """Print trace as JSON."""
    # Remove internal cache before printing
    output = {k: v for k, v in trace.items() if not k.startswith("_")}
    print(json.dumps(output, indent=2))


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

        try:
            # Detect trace type (agent vs graphrag)
            trace_type = detect_trace_type(
                socket=socket,
                flow_id=args.flow_id,
                user=args.user,
                collection=args.collection,
                entity_id=args.question_id,
            )

            if trace_type == "agent":
                # Build and print agent trace
                trace = build_agent_trace(
                    socket=socket,
                    flow_id=args.flow_id,
                    user=args.user,
                    collection=args.collection,
                    session_id=args.question_id,
                    api=api,
                    max_answer=args.max_answer,
                )

                if args.format == 'json':
                    print_agent_json(trace)
                else:
                    print_agent_text(trace)
            else:
                # Build and print GraphRAG trace (existing behavior)
                trace = build_trace(
                    socket=socket,
                    flow_id=args.flow_id,
                    user=args.user,
                    collection=args.collection,
                    question_id=args.question_id,
                    api=api,
                    show_provenance=args.show_provenance,
                    max_answer=args.max_answer,
                )

                if args.format == 'json':
                    print_json(trace)
                else:
                    print_text(trace, show_provenance=args.show_provenance)

        finally:
            socket.close()

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
