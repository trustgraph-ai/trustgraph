#!/usr/bin/env python3

"""
Client utility for browsing and loading documents from the TrustGraph
public document library.

Usage:
    python library_client.py list
    python library_client.py search <text>
    python library_client.py load-all
    python library_client.py load-doc <id>
    python library_client.py load-match <text>
"""

import json
import urllib.request
import sys
import os
import argparse

from trustgraph.api import Api
from trustgraph.api.types import Uri, Literal, Triple

BUCKET_URL = "https://storage.googleapis.com/trustgraph-library"
INDEX_URL = f"{BUCKET_URL}/index.json"

default_url = os.getenv("TRUSTGRAPH_URL", "http://localhost:8088/")
default_user = "trustgraph"
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)


def fetch_index():
    with urllib.request.urlopen(INDEX_URL) as resp:
        return json.loads(resp.read())


def fetch_document_metadata(doc_id):
    url = f"{BUCKET_URL}/{doc_id}.json"
    with urllib.request.urlopen(url) as resp:
        return json.loads(resp.read())


def fetch_document_content(doc_id):
    url = f"{BUCKET_URL}/{doc_id}.epub"
    with urllib.request.urlopen(url) as resp:
        return resp.read()


def search_index(index, query):
    query = query.lower()
    results = []
    for doc in index:
        title = doc.get("title", "").lower()
        comments = doc.get("comments", "").lower()
        tags = [t.lower() for t in doc.get("tags", [])]
        if (query in title or query in comments or
                any(query in t for t in tags)):
            results.append(doc)
    return results


def print_index(index):
    if not index:
        return

    # Calculate column widths
    id_width = max(len(str(doc.get("id", ""))) for doc in index)
    title_width = max(len(doc.get("title", "")) for doc in index)

    # Cap title width for readability
    title_width = min(title_width, 60)
    id_width = max(id_width, 2)

    try:
        term_width = os.get_terminal_size().columns
    except OSError:
        term_width = 120

    tags_width = max(term_width - id_width - title_width - 6, 20)

    header = f"{'ID':<{id_width}}  {'Title':<{title_width}}  {'Tags':<{tags_width}}"
    print(header)
    print("-" * len(header))

    for doc in index:
        eid = str(doc.get("id", ""))
        title = doc.get("title", "")
        if len(title) > title_width:
            title = title[:title_width - 3] + "..."
        tags = ", ".join(doc.get("tags", []))
        if len(tags) > tags_width:
            tags = tags[:tags_width - 3] + "..."
        print(f"{eid:<{id_width}}  {title:<{title_width}}  {tags}")


def convert_value(v):
    """Convert a JSON triple value to a Uri or Literal."""
    if v["type"] == "uri":
        return Uri(v["value"])
    else:
        return Literal(v["value"])


def convert_metadata(metadata_json):
    """Convert JSON metadata triples to Triple objects."""
    triples = []
    for t in metadata_json:
        triples.append(Triple(
            s=convert_value(t["s"]),
            p=convert_value(t["p"]),
            o=convert_value(t["o"]),
        ))
    return triples


def load_document(api, user, doc_entry):
    """Fetch metadata and content for a document, then load into TrustGraph."""
    doc_id = doc_entry["id"]
    title = doc_entry["title"]

    print(f"  [{doc_id}] {title}")

    print(f"    fetching metadata...")
    doc_json = fetch_document_metadata(doc_id)
    doc = doc_json[0]

    print(f"    fetching content...")
    content = fetch_document_content(doc_id)

    print(f"    loading into TrustGraph ({len(content) // 1024}KB)...")
    metadata = convert_metadata(doc["metadata"])

    api.add_document(
        id=doc["id"],
        metadata=metadata,
        user=user,
        kind=doc["kind"],
        title=doc["title"],
        comments=doc["comments"],
        tags=doc["tags"],
        document=content,
    )

    print(f"    done.")


def load_documents(api, user, docs):
    """Load a list of documents."""
    print(f"Loading {len(docs)} document(s)...\n")
    for doc in docs:
        try:
            load_document(api, user, doc)
        except Exception as e:
            print(f"    FAILED: {e}", file=sys.stderr)
        print()
    print("Complete.")


def main():
    parser = argparse.ArgumentParser(
        description="Browse and load documents from the TrustGraph public document library.",
    )

    parser.add_argument(
        "-u", "--url", default=default_url,
        help=f"TrustGraph API URL (default: {default_url})",
    )
    parser.add_argument(
        "-U", "--user", default=default_user,
        help=f"User ID (default: {default_user})",
    )
    parser.add_argument(
        "-t", "--token", default=default_token,
        help="Authentication token (default: $TRUSTGRAPH_TOKEN)",
    )

    sub = parser.add_subparsers(dest="command")

    sub.add_parser("list", help="List all documents")

    search_parser = sub.add_parser("search", help="Search documents")
    search_parser.add_argument("query", help="Text to search for")

    sub.add_parser("load-all", help="Load all documents into TrustGraph")

    load_doc_parser = sub.add_parser("load-doc", help="Load a document by ID")
    load_doc_parser.add_argument("id", help="Document ID (ebook number)")

    load_match_parser = sub.add_parser(
        "load-match", help="Load all documents matching a search term",
    )
    load_match_parser.add_argument("query", help="Text to search for")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    index = fetch_index()

    if args.command in ("list", "search"):
        if args.command == "list":
            print_index(index)
        else:
            results = search_index(index, args.query)
            if results:
                print_index(results)
            else:
                print("No matches found.", file=sys.stderr)
                sys.exit(1)
        return

    # Load commands need the API
    api = Api(args.url, token=args.token).library()

    if args.command == "load-all":
        load_documents(api, args.user, index)

    elif args.command == "load-doc":
        matches = [d for d in index if str(d.get("id")) == args.id]
        if not matches:
            print(f"No document with ID '{args.id}' found.", file=sys.stderr)
            sys.exit(1)
        load_documents(api, args.user, matches)

    elif args.command == "load-match":
        results = search_index(index, args.query)
        if results:
            load_documents(api, args.user, results)
        else:
            print("No matches found.", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
