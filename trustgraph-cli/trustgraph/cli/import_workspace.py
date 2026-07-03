"""
Imports a workspace bundle (.tgx, produced by tg-export-workspace) into a
TrustGraph deployment. The target workspace defaults to the name recorded
in the bundle's manifest and can be renamed with --workspace.

By default existing (type, key) entries in the target workspace are left
untouched and only missing keys are added, matching WorkspaceInit's
re-run behaviour; pass --overwrite to replace every imported key. Use
--dry-run to show what would be written without changing anything.
"""

import argparse
import json
import os
import sys
import tarfile

from trustgraph.api import Api
from trustgraph.api.types import ConfigValue

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)

SUPPORTED_FORMAT = "tgx"
SUPPORTED_FORMAT_VERSION = 1


def _read_bundle(path):
    """Read manifest and config entries from a .tgx bundle."""

    manifest = None
    entries = []

    with tarfile.open(path, "r:gz") as tar:
        for member in tar.getmembers():
            if not member.isfile():
                continue
            f = tar.extractfile(member)
            if f is None:
                continue
            data = f.read()
            if member.name == "manifest.json":
                manifest = json.loads(data)
            elif member.name.startswith("config/") and \
                    member.name.endswith(".json"):
                entries.append(json.loads(data))

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

    return manifest, entries


def import_workspace(
        url, input, workspace=None, overwrite=False, config_only=False,
        dry_run=False, token=None,
):

    manifest, entries = _read_bundle(input)

    # Knowledge import (triples, documents, embeddings) is not implemented
    # yet; refuse to silently drop it from a bundle that carries it.
    if manifest.get("contents", {}).get("knowledge") and not config_only:
        raise RuntimeError(
            "bundle contains knowledge data, which this tool cannot import "
            "yet; re-run with --config-only to import just the configuration"
        )

    target = workspace or manifest.get("workspace") or "default"

    api = Api(url, token=token, workspace=target).config()

    # Mirror WorkspaceInit's re-run behaviour: without --overwrite, keys
    # already present in the target workspace are skipped (per key, not per
    # type). The config API's put is a blanket upsert, so filter client-side.
    existing = {}
    if not overwrite:
        for type_ in sorted({e["type"] for e in entries}):
            existing[type_] = set(api.list(type_))

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
        print(f"Dry run: {len(values)} item(s) would be imported into "
              f"workspace '{target}', {skipped} skipped as existing",
              flush=True)
        return

    if values:
        api.put(values)

    print(f"Imported {len(values)} config item(s) into workspace "
          f"'{target}', {skipped} skipped as existing", flush=True)


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
        '--overwrite',
        action='store_true',
        help='Replace existing keys in the target workspace (default: '
             'keep existing keys and only add missing ones)',
    )

    parser.add_argument(
        '--config-only',
        action='store_true',
        help='Import only the configuration, skipping any knowledge data '
             'in the bundle',
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
            dry_run=args.dry_run,
            token=args.token,
        )

    except Exception as e:

        print("Exception:", e, flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
