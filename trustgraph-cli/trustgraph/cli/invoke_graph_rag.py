"""
Uses the GraphRAG service to answer a question
"""

import argparse
import json
import os
import sys
import websockets
import asyncio
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
default_user = 'trustgraph'
default_collection = 'default'
default_entity_limit = 50
default_triple_limit = 30
default_max_subgraph_size = 150
default_max_path_length = 2

# Provenance predicates
TG = "https://trustgraph.ai/ns/"
TG_QUERY = TG + "query"
TG_CONCEPT = TG + "concept"
TG_ENTITY = TG + "entity"
TG_EDGE_COUNT = TG + "edgeCount"
TG_SELECTED_EDGE = TG + "selectedEdge"
TG_EDGE = TG + "edge"
TG_REASONING = TG + "reasoning"
TG_DOCUMENT = TG + "document"
TG_CONTAINS = TG + "contains"
PROV = "http://www.w3.org/ns/prov#"
PROV_STARTED_AT_TIME = PROV + "startedAtTime"
PROV_WAS_DERIVED_FROM = PROV + "wasDerivedFrom"
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"


def _get_event_type(prov_id):
    """Extract event type from provenance_id"""
    if "question" in prov_id:
        return "question"
    elif "grounding" in prov_id:
        return "grounding"
    elif "exploration" in prov_id:
        return "exploration"
    elif "focus" in prov_id:
        return "focus"
    elif "synthesis" in prov_id:
        return "synthesis"
    return "provenance"


def _format_provenance_details(event_type, triples):
    """Format provenance details based on event type and triples"""
    lines = []

    if event_type == "question":
        # Show query and timestamp
        for s, p, o in triples:
            if p == TG_QUERY:
                lines.append(f"    Query: {o}")
            elif p == PROV_STARTED_AT_TIME:
                lines.append(f"    Time: {o}")

    elif event_type == "grounding":
        # Show extracted concepts
        concepts = [o for s, p, o in triples if p == TG_CONCEPT]
        if concepts:
            lines.append(f"    Concepts: {len(concepts)}")
            for concept in concepts:
                lines.append(f"      - {concept}")

    elif event_type == "exploration":
        # Show edge count (seed entities resolved separately with labels)
        for s, p, o in triples:
            if p == TG_EDGE_COUNT:
                lines.append(f"    Edges explored: {o}")

    elif event_type == "focus":
        # For focus, just count edge selection URIs
        # The actual edge details are fetched separately via edge_selections parameter
        edge_sel_uris = []
        for s, p, o in triples:
            if p == TG_SELECTED_EDGE:
                edge_sel_uris.append(o)
        if edge_sel_uris:
            lines.append(f"    Focused on {len(edge_sel_uris)} edge(s)")

    elif event_type == "synthesis":
        # Show document reference (content already streamed)
        for s, p, o in triples:
            if p == TG_DOCUMENT:
                lines.append(f"    Document: {o}")

    return lines


async def _query_triples_once(ws_url, flow_id, prov_id, user, collection, graph=None, debug=False):
    """Query triples for a provenance node (single attempt)"""
    request = {
        "id": "triples-request",
        "service": "triples",
        "flow": flow_id,
        "request": {
            "s": {"t": "i", "i": prov_id},
            "user": user,
            "collection": collection,
            "limit": 100
        }
    }
    # Add graph filter if specified (for named graph queries)
    if graph is not None:
        request["request"]["g"] = graph

    if debug:
        print(f"    [debug] querying triples for s={prov_id}", file=sys.stderr)

    triples = []
    try:
        async with websockets.connect(ws_url, ping_interval=20, ping_timeout=30) as websocket:
            await websocket.send(json.dumps(request))

            async for raw_message in websocket:
                response = json.loads(raw_message)

                if debug:
                    print(f"    [debug] response: {json.dumps(response)[:200]}", file=sys.stderr)

                if response.get("id") != "triples-request":
                    continue

                if "error" in response:
                    if debug:
                        print(f"    [debug] error: {response['error']}", file=sys.stderr)
                    break

                if "response" in response:
                    resp = response["response"]
                    # Handle triples response
                    # Response format: {"response": [triples...]}
                    # Each triple uses compact keys: "i" for iri, "v" for value, "t" for type
                    triple_list = resp.get("response", [])
                    for t in triple_list:
                        s = t.get("s", {}).get("i", t.get("s", {}).get("v", ""))
                        p = t.get("p", {}).get("i", t.get("p", {}).get("v", ""))
                        # Handle quoted triples (type "t") and regular values
                        o_term = t.get("o", {})
                        if o_term.get("t") == "t":
                            # Quoted triple - extract s, p, o from nested structure
                            tr = o_term.get("tr", {})
                            o = {
                                "s": tr.get("s", {}).get("i", ""),
                                "p": tr.get("p", {}).get("i", ""),
                                "o": tr.get("o", {}).get("i", tr.get("o", {}).get("v", "")),
                            }
                        else:
                            o = o_term.get("i", o_term.get("v", ""))
                        triples.append((s, p, o))

                    if resp.get("complete") or response.get("complete"):
                        break
    except Exception as e:
        if debug:
            print(f"    [debug] exception: {e}", file=sys.stderr)

    if debug:
        print(f"    [debug] got {len(triples)} triples", file=sys.stderr)

    return triples


async def _query_triples(ws_url, flow_id, prov_id, user, collection, graph=None, max_retries=5, retry_delay=0.2, debug=False):
    """Query triples for a provenance node with retries for race condition"""
    for attempt in range(max_retries):
        triples = await _query_triples_once(ws_url, flow_id, prov_id, user, collection, graph=graph, debug=debug)
        if triples:
            return triples
        # Wait before retry if empty (triples may not be stored yet)
        if attempt < max_retries - 1:
            if debug:
                print(f"    [debug] retry {attempt + 1}/{max_retries}...", file=sys.stderr)
            await asyncio.sleep(retry_delay)
    return []


async def _query_edge_provenance(ws_url, flow_id, edge_s, edge_p, edge_o, user, collection, debug=False):
    """
    Query for provenance of an edge (s, p, o) in the knowledge graph.

    Finds subgraphs that contain the edge via tg:contains, then follows
    prov:wasDerivedFrom to find source documents.

    Returns list of source URIs (chunks, pages, documents).
    """
    # Query for subgraphs that contain this edge: ?subgraph tg:contains <<s p o>>
    request = {
        "id": "edge-prov-request",
        "service": "triples",
        "flow": flow_id,
        "request": {
            "p": {"t": "i", "i": TG_CONTAINS},
            "o": {
                "t": "t",  # Quoted triple type
                "tr": {
                    "s": {"t": "i", "i": edge_s},
                    "p": {"t": "i", "i": edge_p},
                    "o": {"t": "i", "i": edge_o} if edge_o.startswith("http") or edge_o.startswith("urn:") else {"t": "l", "v": edge_o},
                }
            },
            "user": user,
            "collection": collection,
            "limit": 10
        }
    }

    if debug:
        print(f"    [debug] querying edge provenance for ({edge_s}, {edge_p}, {edge_o})", file=sys.stderr)

    stmt_uris = []
    try:
        async with websockets.connect(ws_url, ping_interval=20, ping_timeout=30) as websocket:
            await websocket.send(json.dumps(request))

            async for raw_message in websocket:
                response = json.loads(raw_message)

                if response.get("id") != "edge-prov-request":
                    continue

                if "error" in response:
                    if debug:
                        print(f"    [debug] error: {response['error']}", file=sys.stderr)
                    break

                if "response" in response:
                    resp = response["response"]
                    triple_list = resp.get("response", [])
                    for t in triple_list:
                        s = t.get("s", {}).get("i", "")
                        if s:
                            stmt_uris.append(s)

                    if resp.get("complete") or response.get("complete"):
                        break
    except Exception as e:
        if debug:
            print(f"    [debug] exception querying edge provenance: {e}", file=sys.stderr)

    if debug:
        print(f"    [debug] found {len(stmt_uris)} reifying statements", file=sys.stderr)

    # For each statement, query wasDerivedFrom to find sources
    sources = []
    for stmt_uri in stmt_uris:
        # Query: stmt_uri prov:wasDerivedFrom ?source
        request = {
            "id": "derived-from-request",
            "service": "triples",
            "flow": flow_id,
            "request": {
                "s": {"t": "i", "i": stmt_uri},
                "p": {"t": "i", "i": PROV_WAS_DERIVED_FROM},
                "user": user,
                "collection": collection,
                "limit": 10
            }
        }

        try:
            async with websockets.connect(ws_url, ping_interval=20, ping_timeout=30) as websocket:
                await websocket.send(json.dumps(request))

                async for raw_message in websocket:
                    response = json.loads(raw_message)

                    if response.get("id") != "derived-from-request":
                        continue

                    if "error" in response:
                        break

                    if "response" in response:
                        resp = response["response"]
                        triple_list = resp.get("response", [])
                        for t in triple_list:
                            o = t.get("o", {}).get("i", "")
                            if o:
                                sources.append(o)

                        if resp.get("complete") or response.get("complete"):
                            break
        except Exception as e:
            if debug:
                print(f"    [debug] exception querying wasDerivedFrom: {e}", file=sys.stderr)

    if debug:
        print(f"    [debug] found {len(sources)} source(s): {sources}", file=sys.stderr)

    return sources


async def _query_derived_from(ws_url, flow_id, uri, user, collection, debug=False):
    """Query for the prov:wasDerivedFrom parent of a URI. Returns None if no parent."""
    request = {
        "id": "parent-request",
        "service": "triples",
        "flow": flow_id,
        "request": {
            "s": {"t": "i", "i": uri},
            "p": {"t": "i", "i": PROV_WAS_DERIVED_FROM},
            "user": user,
            "collection": collection,
            "limit": 1
        }
    }

    try:
        async with websockets.connect(ws_url, ping_interval=20, ping_timeout=30) as websocket:
            await websocket.send(json.dumps(request))

            async for raw_message in websocket:
                response = json.loads(raw_message)

                if response.get("id") != "parent-request":
                    continue

                if "error" in response:
                    break

                if "response" in response:
                    resp = response["response"]
                    triple_list = resp.get("response", [])
                    if triple_list:
                        return triple_list[0].get("o", {}).get("i", None)

                    if resp.get("complete") or response.get("complete"):
                        break
    except Exception as e:
        if debug:
            print(f"    [debug] exception querying parent: {e}", file=sys.stderr)

    return None


async def _trace_provenance_chain(ws_url, flow_id, source_uri, user, collection, label_cache, debug=False):
    """
    Trace the full provenance chain from a source URI up to the root document.
    Returns a list of (uri, label) tuples from leaf to root.
    """
    chain = []
    current = source_uri
    max_depth = 10  # Prevent infinite loops

    for _ in range(max_depth):
        if not current:
            break

        # Get label for current entity
        label = await _query_label(ws_url, flow_id, current, user, collection, label_cache, debug)
        chain.append((current, label))

        # Get parent
        parent = await _query_derived_from(ws_url, flow_id, current, user, collection, debug)
        if not parent or parent == current:
            break
        current = parent

    return chain


def _format_provenance_chain(chain):
    """
    Format a provenance chain as a human-readable string.
    Chain is [(uri, label), ...] from leaf to root.
    """
    if not chain:
        return ""

    # Show labels, from leaf to root
    labels = [label for uri, label in chain]
    return " → ".join(labels)


def _is_iri(value):
    """Check if a value looks like an IRI."""
    if not isinstance(value, str):
        return False
    return value.startswith("http://") or value.startswith("https://") or value.startswith("urn:")


async def _query_label(ws_url, flow_id, iri, user, collection, label_cache, debug=False):
    """
    Query for the rdfs:label of an IRI.
    Uses label_cache to avoid repeated queries.
    Returns the label if found, otherwise returns the IRI.
    """
    if not _is_iri(iri):
        return iri

    # Check cache first
    if iri in label_cache:
        return label_cache[iri]

    request = {
        "id": "label-request",
        "service": "triples",
        "flow": flow_id,
        "request": {
            "s": {"t": "i", "i": iri},
            "p": {"t": "i", "i": RDFS_LABEL},
            "user": user,
            "collection": collection,
            "limit": 1
        }
    }

    label = iri  # Default to IRI if no label found
    try:
        async with websockets.connect(ws_url, ping_interval=20, ping_timeout=30) as websocket:
            await websocket.send(json.dumps(request))

            async for raw_message in websocket:
                response = json.loads(raw_message)

                if response.get("id") != "label-request":
                    continue

                if "error" in response:
                    break

                if "response" in response:
                    resp = response["response"]
                    triple_list = resp.get("response", [])
                    if triple_list:
                        # Get the label value
                        o = triple_list[0].get("o", {})
                        label = o.get("v", o.get("i", iri))

                    if resp.get("complete") or response.get("complete"):
                        break
    except Exception as e:
        if debug:
            print(f"    [debug] exception querying label for {iri}: {e}", file=sys.stderr)

    # Cache the result
    label_cache[iri] = label
    return label


async def _resolve_edge_labels(ws_url, flow_id, edge_triple, user, collection, label_cache, debug=False):
    """
    Resolve labels for all IRI components of an edge triple.
    Returns (s_label, p_label, o_label).
    """
    s = edge_triple.get("s", "?")
    p = edge_triple.get("p", "?")
    o = edge_triple.get("o", "?")

    s_label = await _query_label(ws_url, flow_id, s, user, collection, label_cache, debug)
    p_label = await _query_label(ws_url, flow_id, p, user, collection, label_cache, debug)
    o_label = await _query_label(ws_url, flow_id, o, user, collection, label_cache, debug)

    return s_label, p_label, o_label


async def _question_explainable(
        url, flow_id, question, user, collection, entity_limit, triple_limit,
        max_subgraph_size, max_path_length, token=None, debug=False
):
    """Execute graph RAG with explainability - shows provenance events with details"""
    # Convert HTTP URL to WebSocket URL
    if url.startswith("http://"):
        ws_url = url.replace("http://", "ws://", 1)
    elif url.startswith("https://"):
        ws_url = url.replace("https://", "wss://", 1)
    else:
        ws_url = f"ws://{url}"

    ws_url = f"{ws_url.rstrip('/')}/api/v1/socket"
    if token:
        ws_url = f"{ws_url}?token={token}"

    # Cache for label lookups to avoid repeated queries
    label_cache = {}

    request = {
        "id": "cli-request",
        "service": "graph-rag",
        "flow": flow_id,
        "request": {
            "query": question,
            "user": user,
            "collection": collection,
            "entity-limit": entity_limit,
            "triple-limit": triple_limit,
            "max-subgraph-size": max_subgraph_size,
            "max-path-length": max_path_length,
            "streaming": True
        }
    }

    async with websockets.connect(ws_url, ping_interval=20, ping_timeout=300) as websocket:
        await websocket.send(json.dumps(request))

        async for raw_message in websocket:
            response = json.loads(raw_message)

            if response.get("id") != "cli-request":
                continue

            if "error" in response:
                print(f"\nError: {response['error']}", file=sys.stderr)
                break

            if "response" in response:
                resp = response["response"]

                # Check for errors in response
                if "error" in resp and resp["error"]:
                    err = resp["error"]
                    print(f"\nError: {err.get('message', 'Unknown error')}", file=sys.stderr)
                    break

                message_type = resp.get("message_type", "")

                if debug:
                    print(f"  [debug] message_type={message_type}, keys={list(resp.keys())}", file=sys.stderr)

                if message_type == "explain":
                    # Display explain event with details
                    explain_id = resp.get("explain_id", "")
                    explain_graph = resp.get("explain_graph")  # Named graph (e.g., urn:graph:retrieval)
                    if explain_id:
                        event_type = _get_event_type(explain_id)
                        print(f"\n  [{event_type}] {explain_id}", file=sys.stderr)

                        # Query triples for this explain node (using named graph filter)
                        triples = await _query_triples(
                            ws_url, flow_id, explain_id, user, collection, graph=explain_graph, debug=debug
                        )

                        # Format and display details
                        details = _format_provenance_details(event_type, triples)
                        for line in details:
                            print(line, file=sys.stderr)

                        # For exploration events, resolve entity labels
                        if event_type == "exploration":
                            entity_iris = [o for s, p, o in triples if p == TG_ENTITY]
                            if entity_iris:
                                print(f"    Seed entities: {len(entity_iris)}", file=sys.stderr)
                                for iri in entity_iris:
                                    label = await _query_label(
                                        ws_url, flow_id, iri, user, collection,
                                        label_cache, debug=debug
                                    )
                                    print(f"      - {label}", file=sys.stderr)

                        # For focus events, query each edge selection for details
                        if event_type == "focus":
                            for s, p, o in triples:
                                if debug:
                                    print(f"    [debug] triple: p={p}, o={o}, o_type={type(o).__name__}", file=sys.stderr)
                                if p == TG_SELECTED_EDGE and isinstance(o, str):
                                    if debug:
                                        print(f"    [debug] querying edge selection: {o}", file=sys.stderr)
                                    # Query the edge selection entity (using named graph filter)
                                    edge_triples = await _query_triples(
                                        ws_url, flow_id, o, user, collection, graph=explain_graph, debug=debug
                                    )
                                    if debug:
                                        print(f"    [debug] got {len(edge_triples)} edge triples", file=sys.stderr)
                                    # Extract edge and reasoning
                                    edge_triple = None  # Store the actual triple for provenance lookup
                                    reasoning = None
                                    for es, ep, eo in edge_triples:
                                        if debug:
                                            print(f"    [debug] edge triple: ep={ep}, eo={eo}", file=sys.stderr)
                                        if ep == TG_EDGE and isinstance(eo, dict):
                                            # eo is a quoted triple dict
                                            edge_triple = eo
                                        elif ep == TG_REASONING:
                                            reasoning = eo
                                    if edge_triple:
                                        # Resolve labels for edge components
                                        s_label, p_label, o_label = await _resolve_edge_labels(
                                            ws_url, flow_id, edge_triple, user, collection,
                                            label_cache, debug=debug
                                        )
                                        print(f"      Edge: ({s_label}, {p_label}, {o_label})", file=sys.stderr)
                                    if reasoning:
                                        r_short = reasoning[:100] + "..." if len(reasoning) > 100 else reasoning
                                        print(f"        Reason: {r_short}", file=sys.stderr)

                                    # Trace edge provenance in the user's collection (not explainability)
                                    if edge_triple:
                                        sources = await _query_edge_provenance(
                                            ws_url, flow_id,
                                            edge_triple.get("s", ""),
                                            edge_triple.get("p", ""),
                                            edge_triple.get("o", ""),
                                            user, collection,  # Use the query collection, not explainability
                                            debug=debug
                                        )
                                        if sources:
                                            for src in sources:
                                                # Trace full chain from source to root document
                                                chain = await _trace_provenance_chain(
                                                    ws_url, flow_id, src, user, collection,
                                                    label_cache, debug=debug
                                                )
                                                chain_str = _format_provenance_chain(chain)
                                                print(f"        Source: {chain_str}", file=sys.stderr)

                elif message_type == "chunk" or not message_type:
                    # Display response chunk
                    chunk = resp.get("response", "")
                    if chunk:
                        print(chunk, end="", flush=True)

                # Check if session is complete
                if resp.get("end_of_session"):
                    break

    print()  # Final newline


def _question_explainable_api(
        url, flow_id, question_text, user, collection, entity_limit, triple_limit,
        max_subgraph_size, max_path_length, token=None, debug=False
):
    """Execute graph RAG with explainability using the new API classes."""
    api = Api(url=url, token=token)
    socket = api.socket()
    flow = socket.flow(flow_id)
    explain_client = ExplainabilityClient(flow, retry_delay=0.2, max_retries=10)

    try:
        # Stream GraphRAG with explainability - process events as they arrive
        for item in flow.graph_rag_explain(
            query=question_text,
            user=user,
            collection=collection,
            max_subgraph_size=max_subgraph_size,
            max_subgraph_count=5,
            max_entity_distance=max_path_length,
        ):
            if isinstance(item, RAGChunk):
                # Print response content
                print(item.content, end="", flush=True)

            elif isinstance(item, ProvenanceEvent):
                # Process provenance event immediately
                prov_id = item.explain_id
                explain_graph = item.explain_graph or "urn:graph:retrieval"

                entity = explain_client.fetch_entity(
                    prov_id,
                    graph=explain_graph,
                    user=user,
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
                            label = explain_client.resolve_label(ent, user, collection)
                            print(f"      - {label}", file=sys.stderr)

                elif isinstance(entity, Focus):
                    print(f"\n  [focus] {prov_id}", file=sys.stderr)
                    if entity.selected_edge_uris:
                        print(f"    Focused on {len(entity.selected_edge_uris)} edge(s)", file=sys.stderr)

                    # Fetch full focus with edge details
                    focus_full = explain_client.fetch_focus_with_edges(
                        prov_id,
                        graph=explain_graph,
                        user=user,
                        collection=collection
                    )
                    if focus_full and focus_full.edge_selections:
                        for edge_sel in focus_full.edge_selections:
                            if edge_sel.edge:
                                # Resolve labels for edge components
                                s_label, p_label, o_label = explain_client.resolve_edge_labels(
                                    edge_sel.edge, user, collection
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
        url, flow_id, question, user, collection, entity_limit, triple_limit,
        max_subgraph_size, max_path_length, streaming=True, token=None,
        explainable=False, debug=False
):

    # Explainable mode uses the API to capture and process provenance events
    if explainable:
        _question_explainable_api(
            url=url,
            flow_id=flow_id,
            question_text=question,
            user=user,
            collection=collection,
            entity_limit=entity_limit,
            triple_limit=triple_limit,
            max_subgraph_size=max_subgraph_size,
            max_path_length=max_path_length,
            token=token,
            debug=debug
        )
        return

    # Create API client
    api = Api(url=url, token=token)

    if streaming:
        # Use socket client for streaming
        socket = api.socket()
        flow = socket.flow(flow_id)

        try:
            response = flow.graph_rag(
                query=question,
                user=user,
                collection=collection,
                entity_limit=entity_limit,
                triple_limit=triple_limit,
                max_subgraph_size=max_subgraph_size,
                max_path_length=max_path_length,
                streaming=True
            )

            # Stream output
            for chunk in response:
                print(chunk, end="", flush=True)
            print()  # Final newline

        finally:
            socket.close()
    else:
        # Use REST API for non-streaming
        flow = api.flow().id(flow_id)
        resp = flow.graph_rag(
            query=question,
            user=user,
            collection=collection,
            entity_limit=entity_limit,
            triple_limit=triple_limit,
            max_subgraph_size=max_subgraph_size,
            max_path_length=max_path_length
        )
        print(resp)

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
        '-U', '--user',
        default=default_user,
        help=f'User ID (default: {default_user})'
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

    args = parser.parse_args()

    try:

        question(
            url=args.url,
            flow_id=args.flow_id,
            question=args.question,
            user=args.user,
            collection=args.collection,
            entity_limit=args.entity_limit,
            triple_limit=args.triple_limit,
            max_subgraph_size=args.max_subgraph_size,
            max_path_length=args.max_path_length,
            streaming=not args.no_streaming,
            token=args.token,
            explainable=args.explainable,
            debug=args.debug,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()
