"""
Show document hierarchy: Document -> Pages -> Chunks -> Edges.

Given a document ID, traverses and displays all derived entities
(pages, chunks, extracted edges) using prov:wasDerivedFrom relationships.

Examples:
  tg-show-document-hierarchy -U trustgraph -C default "urn:trustgraph:doc:abc123"
  tg-show-document-hierarchy --show-content --max-content 500 "urn:trustgraph:doc:abc123"
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
PROV_WAS_DERIVED_FROM = "http://www.w3.org/ns/prov#wasDerivedFrom"
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
TG = "https://trustgraph.ai/ns/"
TG_REIFIES = TG + "reifies"
DC_TITLE = "http://purl.org/dc/terms/title"
DC_FORMAT = "http://purl.org/dc/terms/format"

# Source graph
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


def get_node_metadata(socket, flow_id, user, collection, node_uri):
    """Get metadata for a node (label, type, title, format)."""
    triples = query_triples(socket, flow_id, user, collection, s=node_uri, g=SOURCE_GRAPH)

    metadata = {"uri": node_uri}
    for s, p, o in triples:
        if p == RDFS_LABEL:
            metadata["label"] = o
        elif p == RDF_TYPE:
            metadata["type"] = o
        elif p == DC_TITLE:
            metadata["title"] = o
        elif p == DC_FORMAT:
            metadata["format"] = o

    return metadata


def get_children(socket, flow_id, user, collection, parent_uri):
    """Get children of a node via prov:wasDerivedFrom."""
    triples = query_triples(
        socket, flow_id, user, collection,
        p=PROV_WAS_DERIVED_FROM, o=parent_uri, g=SOURCE_GRAPH
    )
    return [s for s, p, o in triples]


def get_edges_from_chunk(socket, flow_id, user, collection, chunk_uri):
    """Get edges that were derived from a chunk (via tg:reifies)."""
    # Query for triples where: ?stmt prov:wasDerivedFrom chunk_uri
    # Then get the tg:reifies value
    derived_triples = query_triples(
        socket, flow_id, user, collection,
        p=PROV_WAS_DERIVED_FROM, o=chunk_uri, g=SOURCE_GRAPH
    )

    edges = []
    for stmt_uri, _, _ in derived_triples:
        # Get what this statement reifies
        reifies_triples = query_triples(
            socket, flow_id, user, collection,
            s=stmt_uri, p=TG_REIFIES, g=SOURCE_GRAPH
        )
        for _, _, edge in reifies_triples:
            if isinstance(edge, dict):
                edges.append(edge)

    return edges


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


def classify_uri(uri):
    """Classify a URI as document, page, or chunk based on patterns."""
    if not isinstance(uri, str):
        return "unknown"

    # Common patterns in trustgraph URIs
    if "/c" in uri and uri.split("/c")[-1].isdigit():
        return "chunk"
    if "/p" in uri and any(uri.split("/p")[-1].replace("/", "").isdigit() for _ in [1]):
        # Check for page pattern like /p1 or /p1/
        parts = uri.split("/p")
        if len(parts) > 1:
            remainder = parts[-1].split("/")[0]
            if remainder.isdigit():
                return "page"

    if "chunk" in uri.lower():
        return "chunk"
    if "page" in uri.lower():
        return "page"
    if "doc" in uri.lower():
        return "document"

    return "unknown"


def build_hierarchy(socket, flow_id, user, collection, root_uri, api=None, show_content=False, max_content=200, visited=None):
    """Build document hierarchy tree recursively."""
    if visited is None:
        visited = set()

    if root_uri in visited:
        return None
    visited.add(root_uri)

    metadata = get_node_metadata(socket, flow_id, user, collection, root_uri)
    node_type = classify_uri(root_uri)

    node = {
        "uri": root_uri,
        "type": node_type,
        "metadata": metadata,
        "children": [],
        "edges": [],
    }

    # Fetch content if requested
    if show_content and api:
        content = get_document_content(api, user, root_uri, max_content)
        if content:
            node["content"] = content

    # Get children
    children_uris = get_children(socket, flow_id, user, collection, root_uri)

    for child_uri in children_uris:
        child_type = classify_uri(child_uri)

        # Recursively build hierarchy for pages and chunks
        if child_type in ("page", "chunk", "unknown"):
            child_node = build_hierarchy(
                socket, flow_id, user, collection, child_uri,
                api=api, show_content=show_content, max_content=max_content,
                visited=visited
            )
            if child_node:
                node["children"].append(child_node)

    # Get edges for chunks
    if node_type == "chunk":
        edges = get_edges_from_chunk(socket, flow_id, user, collection, root_uri)
        node["edges"] = edges

    # Sort children by URI for consistent output
    node["children"].sort(key=lambda x: x.get("uri", ""))

    return node


def format_edge(edge):
    """Format an edge (quoted triple) for display."""
    if isinstance(edge, dict):
        s = edge.get("s", "?")
        p = edge.get("p", "?")
        o = edge.get("o", "?")

        # Shorten URIs for display
        s_short = s.split("/")[-1] if "/" in str(s) else s
        p_short = p.split("/")[-1] if "/" in str(p) else p
        o_short = o.split("/")[-1] if "/" in str(o) else o

        return f"({s_short}, {p_short}, {o_short})"
    return str(edge)


def print_tree(node, prefix="", is_last=True, show_content=False):
    """Print node as indented tree."""
    connector = "└── " if is_last else "├── "
    continuation = "    " if is_last else "│   "

    # Format node header
    uri = node.get("uri", "")
    node_type = node.get("type", "unknown")
    metadata = node.get("metadata", {})

    label = metadata.get("label") or metadata.get("title") or uri.split("/")[-1]
    type_str = node_type.capitalize()

    if prefix:
        print(f"{prefix}{connector}{type_str}: {label}")
    else:
        print(f"{type_str}: {uri}")
        if metadata.get("title"):
            print(f"  Title: \"{metadata['title']}\"")
        if metadata.get("format"):
            print(f"  Type: {metadata['format']}")

    new_prefix = prefix + continuation if prefix else "  "

    # Print content if available
    if show_content and "content" in node:
        content = node["content"]
        content_lines = content.split("\n")[:3]  # Show first 3 lines
        for line in content_lines:
            if line.strip():
                truncated = line[:80] + "..." if len(line) > 80 else line
                print(f"{new_prefix}Content: \"{truncated}\"")
                break

    # Print edges
    edges = node.get("edges", [])
    children = node.get("children", [])

    total_items = len(edges) + len(children)
    current_item = 0

    for edge in edges:
        current_item += 1
        is_last_item = (current_item == total_items)
        edge_connector = "└── " if is_last_item else "├── "
        print(f"{new_prefix}{edge_connector}Edge: {format_edge(edge)}")

    # Print children recursively
    for i, child in enumerate(children):
        current_item += 1
        is_last_child = (i == len(children) - 1)
        print_tree(child, new_prefix, is_last_child, show_content)


def print_json(node):
    """Print node as JSON."""
    print(json.dumps(node, indent=2))


def main():
    parser = argparse.ArgumentParser(
        prog='tg-show-document-hierarchy',
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        'document_id',
        help='Document URI to show hierarchy for',
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
        '--show-content',
        action='store_true',
        help='Include blob/document content',
    )

    parser.add_argument(
        '--max-content',
        type=int,
        default=200,
        help='Max chars to display per blob (default: 200)',
    )

    parser.add_argument(
        '--format',
        choices=['tree', 'json'],
        default='tree',
        help='Output format: tree (default), json',
    )

    args = parser.parse_args()

    try:
        api = Api(args.api_url, token=args.token)
        socket = api.socket()

        try:
            hierarchy = build_hierarchy(
                socket=socket,
                flow_id=args.flow_id,
                user=args.user,
                collection=args.collection,
                root_uri=args.document_id,
                api=api if args.show_content else None,
                show_content=args.show_content,
                max_content=args.max_content,
            )

            if hierarchy is None:
                print(f"No data found for document: {args.document_id}", file=sys.stderr)
                sys.exit(1)

            if args.format == 'json':
                print_json(hierarchy)
            else:
                print_tree(hierarchy, show_content=args.show_content)

        finally:
            socket.close()

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
