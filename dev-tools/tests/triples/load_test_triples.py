#!/usr/bin/env python3
"""
Load test triples into the triple store for testing tg-query-graph.

Tests all graph features:
- SPO with IRI objects
- SPO with literal objects
- Literals with XML datatypes
- Literals with language tags
- Quoted triples (RDF-star)
- Named graphs
"""

import asyncio
import json
import os
import websockets

# Configuration
API_URL = os.getenv("TRUSTGRAPH_URL", "http://localhost:8088/")
TOKEN = os.getenv("TRUSTGRAPH_TOKEN", None)
FLOW = "default"
USER = "trustgraph"
COLLECTION = "default"
DOCUMENT_ID = "test-triples-001"

# Namespaces
EX = "http://example.org/"
RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RDFS = "http://www.w3.org/2000/01/rdf-schema#"
XSD = "http://www.w3.org/2001/XMLSchema#"
TG = "https://trustgraph.ai/ns/"


def iri(value):
    """Build IRI term."""
    return {"t": "i", "i": value}


def literal(value, datatype=None, language=None):
    """Build literal term with optional datatype or language."""
    term = {"t": "l", "v": value}
    if datatype:
        term["dt"] = datatype
    if language:
        term["ln"] = language
    return term


def quoted_triple(s, p, o):
    """Build quoted triple term (RDF-star)."""
    return {
        "t": "t",
        "tr": {"s": s, "p": p, "o": o}
    }


def triple(s, p, o, g=None):
    """Build a complete triple dict."""
    t = {"s": s, "p": p, "o": o}
    if g:
        t["g"] = g
    return t


# Test triples covering all features
TEST_TRIPLES = [
    # 1. Basic SPO with IRI object
    triple(
        iri(f"{EX}marie-curie"),
        iri(f"{RDF}type"),
        iri(f"{EX}Scientist")
    ),

    # 2. SPO with IRI object (relationship)
    triple(
        iri(f"{EX}marie-curie"),
        iri(f"{EX}discovered"),
        iri(f"{EX}radium")
    ),

    # 3. Simple literal (no datatype/language)
    triple(
        iri(f"{EX}marie-curie"),
        iri(f"{RDFS}label"),
        literal("Marie Curie")
    ),

    # 4. Literal with language tag (English)
    triple(
        iri(f"{EX}marie-curie"),
        iri(f"{RDFS}label"),
        literal("Marie Curie", language="en")
    ),

    # 5. Literal with language tag (French)
    triple(
        iri(f"{EX}marie-curie"),
        iri(f"{RDFS}label"),
        literal("Marie Curie", language="fr")
    ),

    # 6. Literal with language tag (Polish)
    triple(
        iri(f"{EX}marie-curie"),
        iri(f"{RDFS}label"),
        literal("Maria Sk\u0142odowska-Curie", language="pl")
    ),

    # 7. Literal with xsd:integer datatype
    triple(
        iri(f"{EX}marie-curie"),
        iri(f"{EX}birthYear"),
        literal("1867", datatype=f"{XSD}integer")
    ),

    # 8. Literal with xsd:date datatype
    triple(
        iri(f"{EX}marie-curie"),
        iri(f"{EX}birthDate"),
        literal("1867-11-07", datatype=f"{XSD}date")
    ),

    # 9. Literal with xsd:boolean datatype
    triple(
        iri(f"{EX}marie-curie"),
        iri(f"{EX}nobelLaureate"),
        literal("true", datatype=f"{XSD}boolean")
    ),

    # 10. Quoted triple in object position (RDF 1.2 style)
    # "Wikipedia asserts that Marie Curie discovered radium"
    triple(
        iri(f"{EX}wikipedia"),
        iri(f"{TG}asserts"),
        quoted_triple(
            iri(f"{EX}marie-curie"),
            iri(f"{EX}discovered"),
            iri(f"{EX}radium")
        )
    ),

    # 11. Quoted triple with literal inside (object position)
    # "NLP-v1.0 extracted that Marie Curie has label Marie Curie"
    triple(
        iri(f"{EX}nlp-v1"),
        iri(f"{TG}extracted"),
        quoted_triple(
            iri(f"{EX}marie-curie"),
            iri(f"{RDFS}label"),
            literal("Marie Curie")
        )
    ),

    # 12. Triple in a named graph (g is plain string, not Term)
    triple(
        iri(f"{EX}radium"),
        iri(f"{RDF}type"),
        iri(f"{EX}Element"),
        g=f"{EX}chemistry-graph"
    ),

    # 13. Another triple in the same named graph
    triple(
        iri(f"{EX}radium"),
        iri(f"{EX}atomicNumber"),
        literal("88", datatype=f"{XSD}integer"),
        g=f"{EX}chemistry-graph"
    ),

    # 14. Triple in a different named graph
    triple(
        iri(f"{EX}pierre-curie"),
        iri(f"{EX}spouseOf"),
        iri(f"{EX}marie-curie"),
        g=f"{EX}biography-graph"
    ),
]


async def load_triples():
    """Load test triples via WebSocket bulk import."""
    # Convert HTTP URL to WebSocket URL
    ws_url = API_URL.replace("http://", "ws://").replace("https://", "wss://")
    ws_url = f"{ws_url.rstrip('/')}/api/v1/flow/{FLOW}/import/triples"
    if TOKEN:
        ws_url = f"{ws_url}?token={TOKEN}"

    metadata = {
        "id": DOCUMENT_ID,
        "metadata": [],
        "user": USER,
        "collection": COLLECTION
    }

    print(f"Connecting to {ws_url}...")
    async with websockets.connect(ws_url, ping_interval=20, ping_timeout=60) as websocket:
        message = {
            "metadata": metadata,
            "triples": TEST_TRIPLES
        }
        print(f"Sending {len(TEST_TRIPLES)} test triples...")
        await websocket.send(json.dumps(message))
        print("Triples sent successfully!")

    print("\nTest triples loaded:")
    print("  - 2 basic IRI triples (type, relationship)")
    print("  - 4 literal triples (plain + 3 languages: en, fr, pl)")
    print("  - 3 typed literal triples (xsd:integer, xsd:date, xsd:boolean)")
    print("  - 2 quoted triples (RDF-star provenance)")
    print("  - 3 triples in named graphs (chemistry-graph, biography-graph)")
    print(f"\nTotal: {len(TEST_TRIPLES)} triples")
    print(f"User: {USER}, Collection: {COLLECTION}")


def main():
    print("Loading test triples for tg-query-graph testing\n")
    asyncio.run(load_triples())
    print("\nDone! Now test with:")
    print("  tg-query-graph -s http://example.org/marie-curie")
    print("  tg-query-graph -p http://www.w3.org/2000/01/rdf-schema#label")
    print("  tg-query-graph -o 'Marie Curie' --object-language en")
    print("  tg-query-graph --format json | jq .")


if __name__ == "__main__":
    main()
