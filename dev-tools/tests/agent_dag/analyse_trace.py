#!/usr/bin/env python3
"""
Analyse a captured agent trace JSON file and check DAG integrity.

Usage:
    python analyse_trace.py react.json
    python analyse_trace.py -u http://localhost:8088/ react.json
"""

import argparse
import asyncio
import json
import os
import sys
import websockets

DEFAULT_URL = os.getenv("TRUSTGRAPH_URL", "http://localhost:8088/")
DEFAULT_USER = "trustgraph"
DEFAULT_COLLECTION = "default"
DEFAULT_FLOW = "default"
GRAPH = "urn:graph:retrieval"

# Namespace prefixes
PROV = "http://www.w3.org/ns/prov#"
RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RDFS = "http://www.w3.org/2000/01/rdf-schema#"
TG = "https://trustgraph.ai/ns/"

PROV_WAS_DERIVED_FROM = PROV + "wasDerivedFrom"
RDF_TYPE = RDF + "type"

TG_ANALYSIS = TG + "Analysis"
TG_TOOL_USE = TG + "ToolUse"
TG_OBSERVATION_TYPE = TG + "Observation"
TG_CONCLUSION = TG + "Conclusion"
TG_SYNTHESIS = TG + "Synthesis"
TG_QUESTION = TG + "Question"


def shorten(uri):
    """Shorten a URI for display."""
    for prefix, short in [
        (PROV, "prov:"), (RDF, "rdf:"), (RDFS, "rdfs:"), (TG, "tg:"),
    ]:
        if isinstance(uri, str) and uri.startswith(prefix):
            return short + uri[len(prefix):]
    return str(uri)


async def fetch_triples(ws, flow, subject, user, collection, request_counter):
    """Query triples for a given subject URI."""
    request_counter[0] += 1
    req_id = f"q-{request_counter[0]}"

    msg = {
        "id": req_id,
        "service": "triples",
        "flow": flow,
        "request": {
            "s": {"t": "i", "i": subject},
            "g": GRAPH,
            "user": user,
            "collection": collection,
            "limit": 100,
        },
    }

    await ws.send(json.dumps(msg))

    while True:
        raw = await ws.recv()
        resp = json.loads(raw)
        if resp.get("id") == req_id:
            inner = resp.get("response", {})
            if isinstance(inner, dict):
                return inner.get("response", [])
            return inner


def extract_term(term):
    """Extract value from wire-format term."""
    if not term:
        return ""
    t = term.get("t", "")
    if t == "i":
        return term.get("i", "")
    elif t == "l":
        return term.get("v", "")
    elif t == "t":
        tr = term.get("tr", {})
        return {
            "s": extract_term(tr.get("s", {})),
            "p": extract_term(tr.get("p", {})),
            "o": extract_term(tr.get("o", {})),
        }
    return str(term)


def parse_triples(wire_triples):
    """Convert wire triples to (s, p, o) tuples."""
    result = []
    for t in wire_triples:
        s = extract_term(t.get("s", {}))
        p = extract_term(t.get("p", {}))
        o = extract_term(t.get("o", {}))
        result.append((s, p, o))
    return result


def get_types(tuples):
    """Get rdf:type values from parsed triples."""
    return {o for s, p, o in tuples if p == RDF_TYPE}


def get_derived_from(tuples):
    """Get prov:wasDerivedFrom targets from parsed triples."""
    return [o for s, p, o in tuples if p == PROV_WAS_DERIVED_FROM]


async def analyse(path, url, flow, user, collection):
    with open(path) as f:
        messages = json.load(f)

    print(f"Total messages: {len(messages)}")
    print()

    # ---- Pass 1: collect explain IDs and check streaming chunks ----

    explain_ids = []
    errors = []

    for i, msg in enumerate(messages):
        resp = msg.get("response", {})
        chunk_type = resp.get("chunk_type", "?")

        if chunk_type == "explain":
            explain_id = resp.get("explain_id", "")
            explain_ids.append(explain_id)
            print(f"  {i:3d}  {chunk_type}  {explain_id}")
        else:
            print(f"  {i:3d}  {chunk_type}")

        # Rule 7: message_id on content chunks
        if chunk_type in ("thought", "observation", "answer"):
            mid = resp.get("message_id", "")
            if not mid:
                errors.append(
                    f"[msg {i}] {chunk_type} chunk missing message_id"
                )

    print()
    print(f"Explain IDs ({len(explain_ids)}):")
    for eid in explain_ids:
        print(f"  {eid}")

    # ---- Pass 2: fetch triples for each explain ID ----

    ws_url = url.replace("http://", "ws://").replace("https://", "wss://")
    ws_url = f"{ws_url.rstrip('/')}/api/v1/socket"

    request_counter = [0]
    # entity_id -> parsed triples [(s, p, o), ...]
    entities = {}

    print()
    print("Fetching triples...")
    print()

    async with websockets.connect(ws_url, ping_interval=20, ping_timeout=60) as ws:
        for eid in explain_ids:
            wire = await fetch_triples(
                ws, flow, eid, user, collection, request_counter,
            )

            tuples = parse_triples(wire) if isinstance(wire, list) else []
            entities[eid] = tuples

            print(f"  {eid}")
            for s, p, o in tuples:
                o_short = str(o)
                if len(o_short) > 80:
                    o_short = o_short[:77] + "..."
                print(f"    {shorten(p)} = {o_short}")
            print()

    # ---- Pass 3: check rules ----

    all_ids = set(entities.keys())

    # Collect entity metadata
    roots = []           # entities with no wasDerivedFrom
    conclusions = []     # tg:Conclusion entities
    analyses = []        # tg:Analysis entities
    observations = []    # tg:Observation entities

    for eid, tuples in entities.items():
        types = get_types(tuples)
        parents = get_derived_from(tuples)

        if not tuples:
            errors.append(f"[{eid}] entity has no triples in store")

        if not parents:
            roots.append(eid)

        if TG_CONCLUSION in types:
            conclusions.append(eid)
        if TG_ANALYSIS in types:
            analyses.append(eid)
        if TG_OBSERVATION_TYPE in types:
            observations.append(eid)

        # Rule 4: every non-root entity has wasDerivedFrom
        if parents:
            for parent in parents:
                # Rule 5: parent exists in known entities
                if parent not in all_ids:
                    errors.append(
                        f"[{eid}] wasDerivedFrom target not in explain set: "
                        f"{parent}"
                    )

        # Rule 6: Analysis entities must have ToolUse type
        if TG_ANALYSIS in types and TG_TOOL_USE not in types:
            errors.append(
                f"[{eid}] Analysis entity missing tg:ToolUse type"
            )

    # Rule 1: exactly one root
    if len(roots) == 0:
        errors.append("No root entity found (all have wasDerivedFrom)")
    elif len(roots) > 1:
        errors.append(
            f"Multiple roots ({len(roots)}) — expected exactly 1:"
        )
        for r in roots:
            types = get_types(entities[r])
            type_labels = ", ".join(shorten(t) for t in types)
            errors.append(f"  root: {r} [{type_labels}]")

    # Rule 2: exactly one terminal node (nothing derives from it)
    # Build set of entities that are parents of something
    has_children = set()
    for eid, tuples in entities.items():
        for parent in get_derived_from(tuples):
            has_children.add(parent)

    terminals = [eid for eid in all_ids if eid not in has_children]
    if len(terminals) == 0:
        errors.append("No terminal entity found (cycle?)")
    elif len(terminals) > 1:
        errors.append(
            f"Multiple terminal entities ({len(terminals)}) — expected exactly 1:"
        )
        for t in terminals:
            types = get_types(entities[t])
            type_labels = ", ".join(shorten(ty) for ty in types)
            errors.append(f"  terminal: {t} [{type_labels}]")

    # Rule 8: Observation should not derive from Analysis if a sub-trace
    # exists as a sibling. Check: if an Analysis has both a Question child
    # and an Observation child, the Observation should derive from the
    # sub-trace's Synthesis, not from the Analysis.
    for obs_id in observations:
        obs_parents = get_derived_from(entities[obs_id])
        for parent in obs_parents:
            if parent in entities:
                parent_types = get_types(entities[parent])
                if TG_ANALYSIS in parent_types:
                    # Check if this Analysis also has a Question child
                    # (i.e. a sub-trace exists)
                    has_subtrace = False
                    for other_id, other_tuples in entities.items():
                        if other_id == obs_id:
                            continue
                        other_parents = get_derived_from(other_tuples)
                        other_types = get_types(other_tuples)
                        if (parent in other_parents
                                and TG_QUESTION in other_types):
                            has_subtrace = True
                            break
                    if has_subtrace:
                        errors.append(
                            f"[{obs_id}] Observation derives from Analysis "
                            f"{parent} which has a sub-trace — should derive "
                            f"from the sub-trace's Synthesis instead"
                        )

    # ---- Report ----

    print()
    print("=" * 60)
    if errors:
        print(f"ERRORS ({len(errors)}):")
        print()
        for err in errors:
            print(f"  !! {err}")
    else:
        print("ALL CHECKS PASSED")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="JSON trace file")
    parser.add_argument("-u", "--url", default=DEFAULT_URL)
    parser.add_argument("-f", "--flow", default=DEFAULT_FLOW)
    parser.add_argument("-U", "--user", default=DEFAULT_USER)
    parser.add_argument("-C", "--collection", default=DEFAULT_COLLECTION)
    args = parser.parse_args()

    asyncio.run(analyse(
        args.input, args.url, args.flow,
        args.user, args.collection,
    ))


if __name__ == "__main__":
    main()
