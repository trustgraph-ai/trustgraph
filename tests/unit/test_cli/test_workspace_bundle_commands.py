"""
Tests for tg-export-workspace / tg-import-workspace (.tgx bundle commands).

The Api class is mocked in each command module's namespace (same pattern as
test_config_commands.py); bundles are written to and read from tmp_path so
the archive format itself is exercised end-to-end.
"""

import json
import tarfile
from unittest.mock import Mock, patch

import pytest

from trustgraph.api.types import ConfigValue
from trustgraph.cli.export_workspace import export_workspace
from trustgraph.cli.import_workspace import import_workspace

SAMPLE_CONFIG = {
    "prompt": {
        "extract-concepts": json.dumps({"template": "Extract {{q}}"}),
        "answer": json.dumps({"template": "Answer {{q}}"}),
    },
    "tool": {
        "web-search": json.dumps({"name": "web-search", "kind": "http"}),
    },
}


def make_mock_api():
    mock_config = Mock()
    mock_api = Mock()
    mock_api.config.return_value = mock_config
    return mock_api, mock_config


@pytest.fixture
def bundle(tmp_path):
    """Export SAMPLE_CONFIG to a real .tgx and yield its path."""
    path = tmp_path / "ws.tgx"
    with patch("trustgraph.cli.export_workspace.Api") as api_cls:
        mock_api, mock_config = make_mock_api()
        api_cls.return_value = mock_api
        mock_config.all.return_value = (SAMPLE_CONFIG, "v42")
        export_workspace(
            url="http://api/", workspace="source-ws", output=str(path),
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
        assert manifest["contents"] == {"config": True, "knowledge": False}

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
        with patch("trustgraph.cli.export_workspace.Api") as api_cls:
            mock_api, mock_config = make_mock_api()
            api_cls.return_value = mock_api
            mock_config.all.return_value = (
                {"prompt": {"a/b": json.dumps({"x": 1})}}, "v1",
            )
            export_workspace(
                url="http://api/", workspace="ws", output=str(path),
            )
        with tarfile.open(path, "r:gz") as tar:
            names = tar.getnames()
            entry = json.load(tar.extractfile("config/prompt/a%2Fb.json"))
        assert "config/prompt/a%2Fb.json" in names
        assert entry["key"] == "a/b"


class TestImportWorkspace:

    def test_roundtrip_puts_all_values_with_overwrite(self, bundle):
        with patch("trustgraph.cli.import_workspace.Api") as api_cls:
            mock_api, mock_config = make_mock_api()
            api_cls.return_value = mock_api
            import_workspace(
                url="http://api/", input=str(bundle), overwrite=True,
            )

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
        with patch("trustgraph.cli.import_workspace.Api") as api_cls:
            mock_api, mock_config = make_mock_api()
            api_cls.return_value = mock_api
            import_workspace(
                url="http://api/", input=str(bundle), workspace="staging",
                overwrite=True,
            )
        api_cls.assert_called_once_with(
            "http://api/", token=None, workspace="staging",
        )

    def test_default_skips_existing_keys(self, bundle):
        """WorkspaceInit re-run semantics: only missing keys are written."""
        with patch("trustgraph.cli.import_workspace.Api") as api_cls:
            mock_api, mock_config = make_mock_api()
            api_cls.return_value = mock_api
            mock_config.list.side_effect = lambda t: {
                "prompt": ["extract-concepts"],
                "tool": [],
            }[t]
            import_workspace(url="http://api/", input=str(bundle))

        values = mock_config.put.call_args.args[0]
        assert sorted((v.type, v.key) for v in values) == [
            ("prompt", "answer"),
            ("tool", "web-search"),
        ]

    def test_dry_run_writes_nothing(self, bundle, capsys):
        with patch("trustgraph.cli.import_workspace.Api") as api_cls:
            mock_api, mock_config = make_mock_api()
            api_cls.return_value = mock_api
            import_workspace(
                url="http://api/", input=str(bundle), overwrite=True,
                dry_run=True,
            )
        mock_config.put.assert_not_called()
        out = capsys.readouterr().out
        assert "would import prompt/extract-concepts" in out
        assert "3 item(s) would be imported" in out

    def test_rejects_bundle_without_manifest(self, tmp_path):
        path = tmp_path / "bad.tgx"
        with tarfile.open(path, "w:gz"):
            pass
        with patch("trustgraph.cli.import_workspace.Api"):
            with pytest.raises(RuntimeError, match="manifest.json missing"):
                import_workspace(url="http://api/", input=str(path))

    def test_rejects_newer_format_version(self, tmp_path):
        import io
        path = tmp_path / "future.tgx"
        manifest = json.dumps({
            "format": "tgx", "format_version": 99, "workspace": "w",
            "contents": {"config": True, "knowledge": False},
        }).encode()
        with tarfile.open(path, "w:gz") as tar:
            info = tarfile.TarInfo("manifest.json")
            info.size = len(manifest)
            tar.addfile(info, io.BytesIO(manifest))
        with patch("trustgraph.cli.import_workspace.Api"):
            with pytest.raises(RuntimeError, match="newer than this tool"):
                import_workspace(url="http://api/", input=str(path))

    def test_refuses_knowledge_bundle_without_config_only(self, tmp_path):
        import io
        path = tmp_path / "knowledge.tgx"
        manifest = json.dumps({
            "format": "tgx", "format_version": 1, "workspace": "w",
            "contents": {"config": True, "knowledge": True},
        }).encode()
        with tarfile.open(path, "w:gz") as tar:
            info = tarfile.TarInfo("manifest.json")
            info.size = len(manifest)
            tar.addfile(info, io.BytesIO(manifest))
        with patch("trustgraph.cli.import_workspace.Api"):
            with pytest.raises(RuntimeError, match="--config-only"):
                import_workspace(url="http://api/", input=str(path))

    def test_config_only_flag_allows_knowledge_bundle(self, tmp_path):
        import io
        path = tmp_path / "knowledge.tgx"
        manifest = json.dumps({
            "format": "tgx", "format_version": 1, "workspace": "w",
            "contents": {"config": True, "knowledge": True},
        }).encode()
        with tarfile.open(path, "w:gz") as tar:
            info = tarfile.TarInfo("manifest.json")
            info.size = len(manifest)
            tar.addfile(info, io.BytesIO(manifest))
        with patch("trustgraph.cli.import_workspace.Api") as api_cls:
            mock_api, mock_config = make_mock_api()
            api_cls.return_value = mock_api
            import_workspace(
                url="http://api/", input=str(path), config_only=True,
                overwrite=True,
            )
        # No config entries in this bundle; nothing written, no error.
        mock_config.put.assert_not_called()
