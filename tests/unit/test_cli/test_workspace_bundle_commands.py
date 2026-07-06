"""
Tests for tg-export-workspace / tg-import-workspace (.tgx bundle commands).

The Api class is mocked in each command module's namespace (same pattern as
test_config_commands.py); bundles are written to and read from tmp_path so
the archive format itself is exercised end-to-end, including the Phase-2
knowledge tree (per-collection N-Quads + library documents).
"""

import datetime
import io
import json
import tarfile
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from trustgraph.api.types import ConfigValue, Triple
from trustgraph.cli.export_workspace import export_workspace
from trustgraph.cli.import_workspace import import_workspace

from tests.unit.test_cli.conftest import iri, lit

SAMPLE_CONFIG = {
    "prompt": {
        "extract-concepts": json.dumps({"template": "Extract {{q}}"}),
        "answer": json.dumps({"template": "Answer {{q}}"}),
    },
    "tool": {
        "web-search": json.dumps({"name": "web-search", "kind": "http"}),
    },
}

# Wire-format triples for one collection, incl. a datatyped literal.
WIRE_BATCHES = [[
    {"s": iri("http://ex.com/s"), "p": iri("http://ex.com/p"),
     "o": iri("http://ex.com/o")},
    {"s": iri("http://ex.com/s"), "p": iri("http://ex.com/count"),
     "o": lit("42", d="http://www.w3.org/2001/XMLSchema#integer")},
]]

DOC = SimpleNamespace(
    id="doc-1",
    time=datetime.datetime(2026, 7, 1, 12, 0, 0),
    kind="text/plain",
    title="Policy",
    comments="returns policy",
    metadata=[Triple(s="http://ex.com/doc-1", p="http://ex.com/about",
                     o="returns")],
    tags=["policy"],
    parent_id="",
    document_type="source",
)


def make_mock_api(collections=(), batches=(), docs=(), contents=None):
    """Full-surface Api mock; returns (mock_api, mock_config)."""
    mock_api = Mock()

    mock_config = Mock()
    mock_api.config.return_value = mock_config
    mock_config.all.return_value = (SAMPLE_CONFIG, "v42")

    mock_api.collection.return_value.list_collections.return_value = \
        list(collections)

    flow = mock_api.socket.return_value.flow.return_value
    flow.triples_query_stream.return_value = iter(batches)

    library = mock_api.library.return_value
    library.get_documents.return_value = list(docs)
    library.get_document_content.side_effect = \
        lambda id: (contents or {}).get(id, b"")

    return mock_api, mock_config


def export_bundle(path, collections=(), batches=(), docs=(), contents=None,
                  **kwargs):
    """Export SAMPLE_CONFIG (+ optional knowledge mocks) to path."""
    mock_api, mock_config = make_mock_api(
        collections=collections, batches=batches, docs=docs,
        contents=contents,
    )
    with patch("trustgraph.cli.export_workspace.Api") as api_cls:
        api_cls.return_value = mock_api
        export_workspace(
            url="http://api/", workspace="source-ws", output=str(path),
            **kwargs,
        )
    return mock_api, mock_config


DEFAULT_MANIFEST = {
    "format": "tgx", "format_version": 1, "workspace": "w",
    "contents": {"config": True, "knowledge": True},
}


def write_bundle(path, members, manifest=DEFAULT_MANIFEST):
    """Write a raw .tgx from name -> bytes (manifest added first)."""
    entries = {"manifest.json": json.dumps(manifest).encode(), **members}
    with tarfile.open(path, "w:gz") as tar:
        for name, data in entries.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return path


def run_import(mock_api, input, **kwargs):
    """Run import_workspace against a mocked Api."""
    with patch("trustgraph.cli.import_workspace.Api") as api_cls:
        api_cls.return_value = mock_api
        import_workspace(url="http://api/", input=str(input), **kwargs)
    return api_cls


@pytest.fixture
def bundle(tmp_path):
    """Config-only-shaped bundle (no collections/docs mocked)."""
    path = tmp_path / "ws.tgx"
    export_bundle(path)
    return path


@pytest.fixture
def knowledge_bundle(tmp_path):
    """Bundle with one collection (2 triples) and one document."""
    path = tmp_path / "kws.tgx"
    export_bundle(
        path,
        collections=[SimpleNamespace(collection="research")],
        batches=WIRE_BATCHES,
        docs=[DOC],
        contents={"doc-1": b"Customers may return items."},
    )
    return path


class TestExportWorkspace:

    def test_bundle_contains_manifest_and_per_key_entries(self, bundle):
        with tarfile.open(bundle, "r:gz") as tar:
            names = tar.getnames()
            manifest = json.load(tar.extractfile("manifest.json"))

        assert manifest["format"] == "tgx"
        assert manifest["workspace"] == "source-ws"
        assert manifest["config_version"] == "v42"
        assert manifest["contents"] == {"config": True, "knowledge": True}
        assert manifest["knowledge"] == {
            "collections": [], "documents": 0, "triples": {},
        }

        assert "config/prompt/extract-concepts.json" in names
        assert "config/prompt/answer.json" in names
        assert "config/tool/web-search.json" in names

    def test_entries_are_parsed_and_self_describing(self, bundle):
        with tarfile.open(bundle, "r:gz") as tar:
            entry = json.load(
                tar.extractfile("config/prompt/extract-concepts.json")
            )
        # Values are pretty-printed objects, not double-encoded strings,
        # and each entry embeds its own type/key (filenames are cosmetic).
        assert entry == {
            "type": "prompt",
            "key": "extract-concepts",
            "value": {"template": "Extract {{q}}"},
        }

    def test_path_unsafe_keys_are_quoted_in_filenames(self, tmp_path):
        path = tmp_path / "ws.tgx"
        mock_api, mock_config = make_mock_api()
        mock_config.all.return_value = (
            {"prompt": {"a/b": json.dumps({"x": 1})}}, "v1",
        )
        with patch("trustgraph.cli.export_workspace.Api") as api_cls:
            api_cls.return_value = mock_api
            export_workspace(
                url="http://api/", workspace="ws", output=str(path),
            )
        with tarfile.open(path, "r:gz") as tar:
            names = tar.getnames()
            entry = json.load(tar.extractfile("config/prompt/a%2Fb.json"))
        assert "config/prompt/a%2Fb.json" in names
        assert entry["key"] == "a/b"

    def test_knowledge_tree_written_per_collection_and_document(
            self, knowledge_bundle):
        with tarfile.open(knowledge_bundle, "r:gz") as tar:
            names = tar.getnames()
            manifest = json.load(tar.extractfile("manifest.json"))
            nq = tar.extractfile(
                "knowledge/research/triples.nq").read().decode()
            meta = json.load(
                tar.extractfile("knowledge/library/doc-1.meta.json"))
            content = tar.extractfile(
                "knowledge/library/doc-1.content").read()

        assert manifest["contents"]["knowledge"] is True
        assert manifest["knowledge"] == {
            "collections": ["research"], "documents": 1,
            "triples": {"research": 2},
        }
        assert "knowledge/research/triples.nq" in names
        # N-Quads: one line per triple, graph = the collection IRI, and
        # the datatyped literal keeps its full quoted form.
        lines = [ln for ln in nq.splitlines() if ln]
        assert len(lines) == 2
        assert all("<urn:trustgraph:collection:research>" in ln
                   for ln in lines)
        assert '"42"^^<http://www.w3.org/2001/XMLSchema#integer>' in nq

        assert meta["id"] == "doc-1"
        assert meta["title"] == "Policy"
        assert meta["metadata"] == [{
            "s": "http://ex.com/doc-1", "p": "http://ex.com/about",
            "o": "returns",
        }]
        assert content == b"Customers may return items."

    def test_config_only_skips_knowledge(self, tmp_path):
        path = tmp_path / "co.tgx"
        mock_api, _ = export_bundle(
            path,
            collections=[SimpleNamespace(collection="research")],
            config_only=True,
        )
        with tarfile.open(path, "r:gz") as tar:
            names = tar.getnames()
            manifest = json.load(tar.extractfile("manifest.json"))
        assert manifest["contents"] == {"config": True, "knowledge": False}
        assert "knowledge" not in manifest
        assert not any(n.startswith("knowledge/") for n in names)
        mock_api.collection.return_value.list_collections.assert_not_called()
        mock_api.socket.assert_not_called()
        mock_api.library.assert_not_called()


class TestImportWorkspace:

    def test_roundtrip_puts_all_values_with_overwrite(self, bundle):
        mock_api, mock_config = make_mock_api()
        api_cls = run_import(mock_api, bundle, overwrite=True)

        # Target workspace defaults to the manifest's workspace.
        api_cls.assert_called_once_with(
            "http://api/", token=None, workspace="source-ws",
        )
        values = mock_config.put.call_args.args[0]
        assert sorted((v.type, v.key) for v in values) == [
            ("prompt", "answer"),
            ("prompt", "extract-concepts"),
            ("tool", "web-search"),
        ]
        # Values are re-serialized to JSON strings, as config-svc stores.
        by_key = {(v.type, v.key): v for v in values}
        assert json.loads(by_key[("prompt", "answer")].value) == {
            "template": "Answer {{q}}",
        }
        assert all(isinstance(v, ConfigValue) for v in values)

    def test_workspace_flag_renames_target(self, bundle):
        mock_api, mock_config = make_mock_api()
        api_cls = run_import(
            mock_api, bundle, workspace="staging", overwrite=True,
        )
        api_cls.assert_called_once_with(
            "http://api/", token=None, workspace="staging",
        )

    def test_default_skips_existing_keys(self, bundle):
        """WorkspaceInit re-run semantics: only missing keys are written."""
        mock_api, mock_config = make_mock_api()
        mock_config.list.side_effect = lambda t: {
            "prompt": ["extract-concepts"],
            "tool": [],
        }[t]
        run_import(mock_api, bundle)

        values = mock_config.put.call_args.args[0]
        assert sorted((v.type, v.key) for v in values) == [
            ("prompt", "answer"),
            ("tool", "web-search"),
        ]

    def test_dry_run_writes_nothing(self, bundle, capsys):
        mock_api, mock_config = make_mock_api()
        run_import(mock_api, bundle, overwrite=True, dry_run=True)
        mock_config.put.assert_not_called()
        out = capsys.readouterr().out
        assert "would import prompt/extract-concepts" in out

    def test_rejects_bundle_without_manifest(self, tmp_path):
        path = tmp_path / "bad.tgx"
        with tarfile.open(path, "w:gz"):
            pass
        with patch("trustgraph.cli.import_workspace.Api"):
            with pytest.raises(RuntimeError, match="manifest.json missing"):
                import_workspace(url="http://api/", input=str(path))

    def test_rejects_newer_format_version(self, tmp_path):
        path = write_bundle(
            tmp_path / "future.tgx", {},
            manifest={**DEFAULT_MANIFEST, "format_version": 99},
        )
        with patch("trustgraph.cli.import_workspace.Api"):
            with pytest.raises(RuntimeError, match="newer than this tool"):
                import_workspace(url="http://api/", input=str(path))


class TestImportKnowledge:

    def test_roundtrip_imports_triples_and_documents(self, knowledge_bundle):
        mock_api, mock_config = make_mock_api()
        run_import(mock_api, knowledge_bundle, overwrite=True)

        # Triples land in the bulk import stream for the right collection.
        bulk = mock_api.bulk.return_value
        call = bulk.import_triples.call_args
        assert call.args[0] == "default"  # flow id
        triples = sorted(list(call.args[1]), key=lambda t: t.p)
        assert triples == [
            Triple(s="http://ex.com/s", p="http://ex.com/count", o="42"),
            Triple(s="http://ex.com/s", p="http://ex.com/p",
                   o="http://ex.com/o"),
        ]
        assert call.kwargs["metadata"]["collection"] == "research"

        # The document is recreated with its metadata and content.
        add = mock_api.library.return_value.add_document.call_args
        assert add.kwargs["id"] == "doc-1"
        assert add.kwargs["document"] == b"Customers may return items."
        assert add.kwargs["title"] == "Policy"
        assert add.kwargs["kind"] == "text/plain"
        assert add.kwargs["tags"] == ["policy"]
        assert add.kwargs["metadata"] == [
            Triple(s="http://ex.com/doc-1", p="http://ex.com/about",
                   o="returns"),
        ]
        # No processing unless asked: embeddings re-derivation is opt-in.
        mock_api.library.return_value.start_processing.assert_not_called()

    def test_config_only_skips_knowledge_on_import(self, knowledge_bundle):
        mock_api, mock_config = make_mock_api()
        run_import(mock_api, knowledge_bundle, overwrite=True,
                   config_only=True)
        mock_api.bulk.assert_not_called()
        mock_api.library.return_value.add_document.assert_not_called()
        mock_config.put.assert_called_once()

    def test_dry_run_covers_knowledge(self, knowledge_bundle, capsys):
        mock_api, mock_config = make_mock_api()
        run_import(mock_api, knowledge_bundle, overwrite=True, dry_run=True)
        mock_api.bulk.assert_not_called()
        mock_api.library.return_value.add_document.assert_not_called()
        out = capsys.readouterr().out
        assert "would import 2 triple(s) into collection 'research'" in out
        assert "would import document doc-1" in out

    def test_process_flag_reprocesses_documents(self, knowledge_bundle):
        mock_api, mock_config = make_mock_api()
        run_import(mock_api, knowledge_bundle, overwrite=True, process=True,
                   process_collection="research")
        proc = mock_api.library.return_value.start_processing.call_args
        assert proc.kwargs["document_id"] == "doc-1"
        assert proc.kwargs["flow"] == "default"
        assert proc.kwargs["collection"] == "research"


class TestImportDocumentSkipOverwrite:
    """Live-verified semantics: existing documents skip by default, replace
    with --overwrite (remove + add; the library API has no content update)."""

    def _bundle_with_doc(self, tmp_path):
        return write_bundle(tmp_path / "doc.tgx", {
            "knowledge/library/doc-1.meta.json": json.dumps(
                {"id": "doc-1", "title": "T", "metadata": []}).encode(),
            "knowledge/library/doc-1.content": b"hello",
        })

    def test_existing_document_is_skipped_not_fatal(self, tmp_path):
        path = self._bundle_with_doc(tmp_path)
        mock_api, mock_config = make_mock_api(
            docs=[SimpleNamespace(id="doc-1")],
        )
        run_import(mock_api, path, overwrite=False)
        lib = mock_api.library.return_value
        lib.add_document.assert_not_called()
        lib.remove_document.assert_not_called()

    def test_overwrite_replaces_existing_document(self, tmp_path):
        path = self._bundle_with_doc(tmp_path)
        mock_api, mock_config = make_mock_api(
            docs=[SimpleNamespace(id="doc-1")],
        )
        run_import(mock_api, path, overwrite=True)
        lib = mock_api.library.return_value
        lib.remove_document.assert_called_once_with("doc-1")
        lib.add_document.assert_called_once()


class TestCollectionDiscovery:
    """Live-verified: implicitly-created collections (raw triple loads) are
    queryable but unlisted, so export merges --collection extras and import
    registers what it restores."""

    def test_export_includes_extra_unregistered_collections(self, tmp_path):
        path = tmp_path / "ws.tgx"
        mock_api, _ = export_bundle(
            path,
            collections=[SimpleNamespace(collection="default")],
            batches=[[]],
            extra_collections=["research"],
        )
        with tarfile.open(path, "r:gz") as tar:
            manifest = json.load(tar.extractfile("manifest.json"))
        assert manifest["knowledge"]["collections"] == ["default", "research"]

    def test_import_registers_each_restored_collection(self, tmp_path):
        path = write_bundle(tmp_path / "kb.tgx", {
            "knowledge/research/triples.nq": (
                b'<http://ex.com/s> <http://ex.com/p> "v" '
                b'<urn:trustgraph:collection:research> .\n'
            ),
        })
        mock_api, mock_config = make_mock_api()
        run_import(mock_api, path)
        mock_api.collection.return_value.update_collection.assert_called_once_with(
            "research", name="research",
        )

    def test_registered_collections_are_not_reregistered(self, tmp_path):
        """update_collection is an upsert that clears omitted fields, so a
        collection already in the registry must be left untouched."""
        path = write_bundle(tmp_path / "kb.tgx", {
            "knowledge/research/triples.nq": (
                b'<http://ex.com/s> <http://ex.com/p> "v" '
                b'<urn:trustgraph:collection:research> .\n'
            ),
        })
        mock_api, mock_config = make_mock_api(
            collections=[SimpleNamespace(collection="research")],
        )
        run_import(mock_api, path)
        mock_api.collection.return_value.update_collection.assert_not_called()
