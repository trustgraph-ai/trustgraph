"""
Exports a workspace's full configuration state as a portable .tgx bundle
(a gzipped tar archive) for backup, migration between deployments, or
sharing a pre-configured workspace.

The bundle is human-readable: a manifest.json plus one pretty-printed JSON
file per config key under config/<type>/, so it can be inspected and
hand-edited before import. Each entry file embeds its own type and key, so
filenames are cosmetic. Knowledge export (triples, documents, embeddings)
is not yet included; the manifest records that so future importers can
distinguish config-only bundles.
"""

import argparse
import io
import json
import os
import sys
import tarfile
import time
from urllib.parse import quote

from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")

MANIFEST_FORMAT = "tgx"
MANIFEST_FORMAT_VERSION = 1


def _add_bytes(tar, name, data):
    info = tarfile.TarInfo(name=name)
    info.size = len(data)
    info.mtime = int(time.time())
    tar.addfile(info, io.BytesIO(data))


def export_workspace(url, workspace, output, token=None):

    api = Api(url, token=token, workspace=workspace).config()

    config, version = api.all()

    manifest = {
        "format": MANIFEST_FORMAT,
        "format_version": MANIFEST_FORMAT_VERSION,
        "workspace": workspace,
        "config_version": version,
        "exported_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "contents": {"config": True, "knowledge": False},
    }

    count = 0

    with tarfile.open(output, "w:gz") as tar:

        _add_bytes(
            tar, "manifest.json",
            json.dumps(manifest, indent=2).encode("utf-8"),
        )

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

    print(f"Exported {count} config item(s) from workspace "
          f"'{workspace}' to {output}", flush=True)


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
        '-o', '--output',
        required=True,
        help='Output bundle path, e.g. workspace-default.tgx',
    )

    args = parser.parse_args()

    try:

        export_workspace(
            url=args.api_url,
            workspace=args.workspace,
            output=args.output,
            token=args.token,
        )

    except Exception as e:

        print("Exception:", e, flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
