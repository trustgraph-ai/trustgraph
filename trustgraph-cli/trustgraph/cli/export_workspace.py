"""
Exports a workspace's full state as a portable .tgx bundle (a gzipped tar
archive) for backup, migration between deployments, or sharing a
pre-configured workspace.

The bundle carries the workspace configuration (one pretty-printed JSON
file per config key) and, by default, its knowledge: per-collection
knowledge-graph triples as N-Quads (the collection names the graph) and
the document library (metadata plus content). Pass --config-only to
export just the configuration. Embedding vectors are not exported —
re-processing imported documents through a flow regenerates them.
"""

import argparse
import io
import json
import os
import sys
import tarfile
import tempfile
import time
from urllib.parse import quote

from trustgraph.api import Api

from . nquads import serialize_nquads

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")

MANIFEST_FORMAT = "tgx"
MANIFEST_FORMAT_VERSION = 1

# triples_query_stream is bounded by a limit; exports want "everything", so
# default high and let --triples-limit override for truly huge graphs.
DEFAULT_TRIPLES_LIMIT = 1_000_000


def _add_bytes(tar, name, data):
    info = tarfile.TarInfo(name=name)
    info.size = len(data)
    info.mtime = int(time.time())
    tar.addfile(info, io.BytesIO(data))


def _export_config(tar, config):
    """Write one self-describing JSON file per config key; return count."""
    count = 0
    for type_, entries in sorted(config.items()):
        for key, raw in sorted(entries.items()):

            # Config values are stored as JSON strings; parse so the
            # bundle is pretty-printed and hand-editable. A value that
            # isn't valid JSON is preserved verbatim.
            try:
                value = json.loads(raw)
            except (TypeError, json.JSONDecodeError):
                value = raw

            entry = {"type": type_, "key": key, "value": value}

            # Keys may contain path-unsafe characters; the entry embeds
            # the real key, so the quoted filename is cosmetic only.
            name = f"config/{quote(type_, safe='')}/{quote(key, safe='')}.json"

            _add_bytes(
                tar, name,
                json.dumps(entry, indent=2).encode("utf-8"),
            )

            count += 1
    return count


def _export_triples(tar, api, flow_id, collections, triples_limit):
    """Stream each collection's triples into knowledge/<c>/triples.nq.

    N-Quads are written to a tempfile first (tar members need their size
    upfront), so memory stays flat regardless of knowledge-base size.
    Returns {collection: written} and a total skipped count.
    """
    counts = {}
    skipped_total = 0
    socket = api.socket()
    try:
        flow = socket.flow(flow_id)
        for c in collections:
            graph_iri = f"urn:trustgraph:collection:{quote(c, safe='')}"
            tmp = tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", suffix=".nq", delete=False,
            )
            try:
                with tmp:
                    written, skipped = serialize_nquads(
                        flow.triples_query_stream(
                            s=None, p=None, o=None,
                            collection=c,
                            limit=triples_limit,
                            batch_size=100,
                        ),
                        graph_iri,
                        tmp,
                    )
                if written:
                    tar.add(
                        tmp.name,
                        arcname=(
                            f"knowledge/{quote(c, safe='')}/triples.nq"
                        ),
                    )
                counts[c] = written
                skipped_total += skipped
            finally:
                os.unlink(tmp.name)
    finally:
        socket.close()
    return counts, skipped_total


def _export_library(tar, api):
    """Write each library document's metadata + content; return count."""
    library = api.library()
    count = 0
    for doc in library.get_documents(include_children=True):
        # Content is fetched one document at a time so memory is bounded
        # by the largest single document, not the whole library.
        content = library.get_document_content(doc.id)
        meta = {
            "id": doc.id,
            "time": doc.time.isoformat() if doc.time else None,
            "kind": doc.kind,
            "title": doc.title,
            "comments": doc.comments,
            "metadata": [
                {"s": t.s, "p": t.p, "o": t.o} for t in (doc.metadata or [])
            ],
            "tags": list(doc.tags or []),
            "parent_id": doc.parent_id or "",
            "document_type": getattr(doc, "document_type", "") or "",
        }
        base = f"knowledge/library/{quote(doc.id, safe='')}"
        _add_bytes(
            tar, f"{base}.meta.json",
            json.dumps(meta, indent=2).encode("utf-8"),
        )
        _add_bytes(tar, f"{base}.content", content or b"")
        count += 1
    return count


def export_workspace(
        url, workspace, output, token=None, config_only=False,
        flow_id="default", triples_limit=DEFAULT_TRIPLES_LIMIT,
        extra_collections=(),
):

    api = Api(url, token=token, workspace=workspace)

    config, version = api.config().all()

    # Collection discovery is registry-based: collections created implicitly
    # by raw triple loads (e.g. tg-load-knowledge) are queryable but not
    # listed, so they would silently drop out of the bundle. --collection
    # names them explicitly; the enumeration is printed so what's included
    # is never a guess.
    collections = []
    if not config_only:
        registered = [c.collection for c in api.collection().list_collections()]
        collections = sorted(set(registered) | set(extra_collections))
        print(f"Exporting collections: {', '.join(collections)}", flush=True)

    with tarfile.open(output, "w:gz") as tar:

        config_count = _export_config(tar, config)

        triple_counts = {}
        skipped = 0
        doc_count = 0
        if not config_only:
            triple_counts, skipped = _export_triples(
                tar, api, flow_id, collections, triples_limit,
            )
            doc_count = _export_library(tar, api)

        manifest = {
            "format": MANIFEST_FORMAT,
            "format_version": MANIFEST_FORMAT_VERSION,
            "workspace": workspace,
            "config_version": version,
            "exported_at": time.strftime(
                "%Y-%m-%dT%H:%M:%SZ", time.gmtime(),
            ),
            "contents": {"config": True, "knowledge": not config_only},
        }
        if not config_only:
            manifest["knowledge"] = {
                "collections": collections,
                "documents": doc_count,
                "triples": triple_counts,
            }

        _add_bytes(
            tar, "manifest.json",
            json.dumps(manifest, indent=2).encode("utf-8"),
        )

    summary = f"Exported {config_count} config item(s)"
    if not config_only:
        summary += (
            f", {sum(triple_counts.values())} triple(s) across "
            f"{len(triple_counts)} collection(s), {doc_count} document(s)"
        )
        if skipped:
            summary += f" ({skipped} triple(s) not representable, skipped)"
    print(f"{summary} from workspace '{workspace}' to {output}", flush=True)


def main():

    parser = argparse.ArgumentParser(
        prog='tg-export-workspace',
        description=__doc__,
    )

    parser.add_argument(
        '-u', '--api-url',
        default=default_url,
        help=f'API URL (default: {default_url})',
    )

    parser.add_argument(
        '-t', '--token',
        default=default_token,
        help='API token (default: TRUSTGRAPH_TOKEN environment variable)',
    )

    parser.add_argument(
        '-w', '--workspace',
        default=default_workspace,
        help=f'Workspace to export (default: {default_workspace})',
    )

    parser.add_argument(
        '-c', '--collection',
        action='append',
        default=[],
        help='Additionally export this collection even if it is not '
             'registered in collection management (repeatable)',
    )

    parser.add_argument(
        '-o', '--output',
        required=True,
        help='Output bundle path, e.g. workspace-default.tgx',
    )

    parser.add_argument(
        '-f', '--flow-id',
        default="default",
        help='Flow to query triples through (default: default)',
    )

    parser.add_argument(
        '--config-only',
        action='store_true',
        help='Export only the configuration, skipping knowledge '
             '(triples and library documents)',
    )

    parser.add_argument(
        '--triples-limit',
        type=int,
        default=DEFAULT_TRIPLES_LIMIT,
        help='Maximum triples to export per collection '
             f'(default: {DEFAULT_TRIPLES_LIMIT})',
    )

    args = parser.parse_args()

    try:

        export_workspace(
            url=args.api_url,
            workspace=args.workspace,
            output=args.output,
            token=args.token,
            config_only=args.config_only,
            flow_id=args.flow_id,
            triples_limit=args.triples_limit,
            extra_collections=args.collection,
        )

    except Exception as e:

        print("Exception:", e, flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
