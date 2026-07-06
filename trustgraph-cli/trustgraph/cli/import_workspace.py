"""
Imports a workspace bundle (.tgx, produced by tg-export-workspace) into a
TrustGraph deployment. The target workspace defaults to the name recorded
in the bundle's manifest and can be renamed with --workspace.

Configuration import follows WorkspaceInit's re-run behaviour: existing
(type, key) entries are left untouched and only missing keys are added;
pass --overwrite to replace every imported key. Knowledge import (triples
and library documents) is additive — triples are streamed into the target
collection and documents are added to the library; re-importing the same
bundle twice will duplicate knowledge, not merge it. Use --dry-run to
show what would be written without changing anything, --config-only to
skip a bundle's knowledge, and --process to re-run imported documents
through a flow (which regenerates embeddings, so bundles don't carry
vectors).
"""

import argparse
import json
import os
import sys
import tarfile
import uuid
from urllib.parse import unquote

from trustgraph.api import Api
from trustgraph.api.types import ConfigValue, Triple
from trustgraph.cli.nquads import parse_nquads

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)

SUPPORTED_FORMAT = "tgx"
SUPPORTED_FORMAT_VERSION = 1


def _read_bundle(path):
    """Read manifest, config entries, triples and documents from a .tgx.

    Returns (manifest, config_entries, triples_by_collection, documents)
    where triples_by_collection maps collection -> list[Triple] and
    documents is a list of {meta: dict, content: bytes}.
    """

    manifest = None
    config_entries = []
    triples = {}
    doc_meta = {}
    doc_content = {}

    def member_id(name, prefix, suffix):
        return unquote(name[len(prefix):-len(suffix)])

    with tarfile.open(path, "r:gz") as tar:
        for member in tar.getmembers():
            if not member.isfile():
                continue
            f = tar.extractfile(member)
            if f is None:
                continue
            data = f.read()
            name = member.name

            if name == "manifest.json":
                manifest = json.loads(data)

            elif name.startswith("config/") and name.endswith(".json"):
                config_entries.append(json.loads(data))

            elif name.startswith("knowledge/library/") and \
                    name.endswith(".meta.json"):
                doc_id = member_id(name, "knowledge/library/", ".meta.json")
                doc_meta[doc_id] = json.loads(data)

            elif name.startswith("knowledge/library/") and \
                    name.endswith(".content"):
                doc_id = member_id(name, "knowledge/library/", ".content")
                doc_content[doc_id] = data

            elif name.startswith("knowledge/") and \
                    name.endswith("/triples.nq"):
                collection = member_id(name, "knowledge/", "/triples.nq")
                triples[collection] = parse_nquads(data)

    if manifest is None:
        raise RuntimeError("not a workspace bundle: manifest.json missing")

    if manifest.get("format") != SUPPORTED_FORMAT:
        raise RuntimeError(
            f"unsupported bundle format: {manifest.get('format')!r}"
        )

    if manifest.get("format_version", 0) > SUPPORTED_FORMAT_VERSION:
        raise RuntimeError(
            f"bundle format version {manifest.get('format_version')} is "
            f"newer than this tool supports ({SUPPORTED_FORMAT_VERSION}); "
            "upgrade trustgraph-cli"
        )

    documents = [
        {"meta": meta, "content": doc_content.get(doc_id, b"")}
        for doc_id, meta in doc_meta.items()
    ]

    return manifest, config_entries, triples, documents


def _import_config(api, entries, overwrite, dry_run):
    """Import config entries; returns (imported, skipped) counts."""

    config = api.config()

    # Mirror WorkspaceInit's re-run behaviour: without --overwrite, keys
    # already present in the target workspace are skipped (per key, not per
    # type). The config API's put is a blanket upsert, so filter client-side.
    existing = {}
    if not overwrite:
        for type_ in sorted({e["type"] for e in entries}):
            existing[type_] = set(config.list(type_))

    values = []
    skipped = 0

    for e in entries:
        type_, key, value = e["type"], e["key"], e["value"]
        if not overwrite and key in existing.get(type_, set()):
            skipped += 1
            continue
        # Config values are stored as JSON strings (see WorkspaceInit).
        values.append(
            ConfigValue(type=type_, key=key, value=json.dumps(value))
        )

    if dry_run:
        for v in values:
            print(f"would import {v.type}/{v.key}", flush=True)
    elif values:
        config.put(values)

    return len(values), skipped


def _import_triples(api, flow_id, triples_by_collection, dry_run):
    """Stream each collection's triples into the flow; returns count."""

    # Collections restored by the bulk triples path (unlike document
    # processing) are not auto-registered, and an unregistered collection
    # would silently drop out of a future export. Register only the missing
    # ones: update_collection is an upsert whose omitted fields clear the
    # description/tags that _import_config may have just restored.
    # Best-effort — a registry hiccup shouldn't fail a completed triple
    # import (tg-set-collection is the manual remedy).
    registered = None
    if triples_by_collection and not dry_run:
        try:
            registered = {
                c.collection for c in api.collection().list_collections()
            }
        except Exception as e:
            print(
                f"warning: could not list collections for registration: "
                f"{e} — register manually with tg-set-collection",
                flush=True,
            )

    total = 0
    for collection, triples in sorted(triples_by_collection.items()):
        if dry_run:
            print(
                f"would import {len(triples)} triple(s) into "
                f"collection '{collection}'",
                flush=True,
            )
        else:
            api.bulk().import_triples(
                flow_id,
                triples,
                metadata={
                    "id": f"workspace-import-{uuid.uuid4()}",
                    "metadata": [],
                    "collection": collection,
                },
            )
            if registered is not None and collection not in registered:
                try:
                    api.collection().update_collection(
                        collection, name=collection,
                    )
                except Exception as e:
                    print(
                        f"warning: could not register collection "
                        f"'{collection}': {e} — register manually with "
                        f"tg-set-collection",
                        flush=True,
                    )
        total += len(triples)
    return total


def _import_documents(
        api, documents, flow_id, process, process_collection, overwrite,
        dry_run,
):
    """Add library documents back (children after parents).

    Mirrors the config semantics: documents already present in the target
    workspace are skipped unless --overwrite, which replaces them (the
    library API has no in-place content update, so replace = remove + add).
    Returns (imported, skipped).
    """

    library = api.library()

    existing = set()
    if documents:
        existing = {d.id for d in library.get_documents(include_children=True)}

    # Parents must exist before their children.
    ordered = sorted(
        documents, key=lambda d: bool(d["meta"].get("parent_id")),
    )

    count = 0
    doc_skipped = 0
    for doc in ordered:
        meta = doc["meta"]

        if meta["id"] in existing and not overwrite:
            doc_skipped += 1
            if dry_run:
                print(f"would skip existing document {meta['id']}", flush=True)
            continue

        if dry_run:
            print(f"would import document {meta['id']}", flush=True)
            count += 1
            continue

        if meta["id"] in existing:
            library.remove_document(meta["id"])

        metadata = [
            Triple(s=t["s"], p=t["p"], o=t["o"])
            for t in meta.get("metadata", [])
        ]
        if meta.get("parent_id"):
            library.add_child_document(
                document=doc["content"],
                id=meta["id"],
                parent_id=meta["parent_id"],
                title=meta.get("title", ""),
                comments=meta.get("comments", ""),
                kind=meta.get("kind", "text/plain"),
                tags=meta.get("tags", []),
                metadata=metadata,
            )
        else:
            library.add_document(
                document=doc["content"],
                id=meta["id"],
                metadata=metadata,
                title=meta.get("title", ""),
                comments=meta.get("comments", ""),
                kind=meta.get("kind", "text/plain"),
                tags=meta.get("tags", []),
            )

        # Re-processing regenerates extraction output and embeddings for
        # the imported content (bundles carry no vectors).
        if process:
            library.start_processing(
                id=f"proc-{uuid.uuid4()}",
                document_id=meta["id"],
                flow=flow_id,
                collection=process_collection,
                tags=meta.get("tags", []),
            )

        count += 1
    return count, doc_skipped


def import_workspace(
        url, input, workspace=None, overwrite=False, config_only=False,
        flow_id="default", process=False, process_collection="default",
        dry_run=False, token=None,
):

    manifest, config_entries, triples, documents = _read_bundle(input)

    target = workspace or manifest.get("workspace") or "default"

    api = Api(url, token=token, workspace=target)

    imported, skipped = _import_config(
        api, config_entries, overwrite, dry_run,
    )

    triple_count = 0
    doc_count = 0
    has_knowledge = bool(triples or documents)
    if has_knowledge and not config_only:
        triple_count = _import_triples(api, flow_id, triples, dry_run)
        doc_count, doc_skipped = _import_documents(
            api, documents, flow_id, process, process_collection, overwrite,
            dry_run,
        )

    verb = "Dry run:" if dry_run else "Imported"
    summary = (
        f"{verb} {imported} config item(s) into workspace '{target}', "
        f"{skipped} skipped as existing"
    )
    if has_knowledge and not config_only:
        summary += (
            f"; {triple_count} triple(s), {doc_count} document(s)"
            f" ({doc_skipped} skipped as existing)"
        )
    elif has_knowledge:
        summary += "; knowledge skipped (--config-only)"
    print(summary, flush=True)


def main():

    parser = argparse.ArgumentParser(
        prog='tg-import-workspace',
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
        '-i', '--input',
        required=True,
        help='Input bundle path, e.g. workspace-default.tgx',
    )

    parser.add_argument(
        '-w', '--workspace',
        default=None,
        help='Target workspace (default: the workspace recorded in the '
             'bundle manifest)',
    )

    parser.add_argument(
        '-f', '--flow-id',
        default="default",
        help='Flow to import triples through and process documents with '
             '(default: default)',
    )

    parser.add_argument(
        '--overwrite',
        action='store_true',
        help='Replace existing config keys in the target workspace '
             '(default: keep existing keys and only add missing ones)',
    )

    parser.add_argument(
        '--config-only',
        action='store_true',
        help='Import only the configuration, skipping any knowledge data '
             'in the bundle',
    )

    parser.add_argument(
        '--process',
        action='store_true',
        help='Re-process imported documents through the flow after import '
             '(regenerates extraction output and embeddings)',
    )

    parser.add_argument(
        '--process-collection',
        default="default",
        help='Collection that --process targets (default: default)',
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be imported without writing anything',
    )

    args = parser.parse_args()

    try:

        import_workspace(
            url=args.api_url,
            input=args.input,
            workspace=args.workspace,
            overwrite=args.overwrite,
            config_only=args.config_only,
            flow_id=args.flow_id,
            process=args.process,
            process_collection=args.process_collection,
            dry_run=args.dry_run,
            token=args.token,
        )

    except Exception as e:

        print("Exception:", e, flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
