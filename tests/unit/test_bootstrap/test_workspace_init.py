"""Unit tests for trustgraph.bootstrap.initialisers.WorkspaceInit."""

from trustgraph.bootstrap.initialisers.workspace_init import WorkspaceInit


def test_default_iam_timeout():
    init = WorkspaceInit()
    assert init.iam_timeout == 10


def test_iam_timeout_override_is_stored():
    init = WorkspaceInit(iam_timeout=42)
    assert init.iam_timeout == 42
