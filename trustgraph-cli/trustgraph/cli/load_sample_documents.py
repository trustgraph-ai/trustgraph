"""
Loads sample documents into the TrustGraph library from bundled package data.
"""

import argparse
import json
import os
from importlib import resources

from trustgraph.api import Api
from trustgraph.api.types import Uri, Literal, Triple

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")

SAMPLE_DOCS_PACKAGE = "trustgraph.cli.sample_documents"


def get_data_path():
    return resources.files(SAMPLE_DOCS_PACKAGE)


def load_metadata():
    data_path = get_data_path()
    metadata_file = data_path / "metadata.json"
    return json.loads(metadata_file.read_text(encoding="utf-8"))


def convert_value(v):
    if v["type"] == "uri":
        return Uri(v["value"])
    else:
        return Literal(v["value"])


def convert_metadata(metadata_json):
    triples = []
    for t in metadata_json:
        triples.append(Triple(
            s=convert_value(t["s"]),
            p=convert_value(t["p"]),
            o=convert_value(t["o"]),
        ))
    return triples


def load_document(api, doc_entry, data_path):

    doc_id = doc_entry["id"]
    title = doc_entry["title"]
    filename = doc_entry["file"]

    print(f"  [{filename}] {title}")

    print(f"    reading content...")
    content_file = data_path / filename
    content = content_file.read_bytes()

    print(f"    loading into TrustGraph ({len(content) // 1024}KB)...")
    metadata = convert_metadata(doc_entry["metadata"])

    api.add_document(
        id=doc_id,
        metadata=metadata,
        kind=doc_entry["kind"],
        title=title,
        comments=doc_entry["comments"],
        tags=doc_entry["tags"],
        document=content,
    )

    print(f"    done.")


def main():

    parser = argparse.ArgumentParser(
        prog='tg-load-sample-documents',
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

    args = parser.parse_args()

    try:

        api = Api(args.url, token=args.token, workspace=args.workspace)
        library = api.library()

        data_path = get_data_path()
        documents = load_metadata()

        print(f"Loading {len(documents)} sample document(s)...\n")

        for doc in documents:
            try:
                load_document(library, doc, data_path)
            except Exception as e:
                print(f"    FAILED: {e}")
            print()

        print("Complete.")

    except Exception as e:
        print(f"Exception: {e}")
        raise e


if __name__ == "__main__":
    main()
