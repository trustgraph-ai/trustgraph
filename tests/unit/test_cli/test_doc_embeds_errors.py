"""
Unit tests for error handling in the doc-embeds CLI tools.

Both modules run their argument parser at import time, so they cannot be
imported directly.  _load_module() executes everything up to that point and
hands back the module namespace.
"""

import ast
import asyncio
import io
import types
from pathlib import Path

import msgpack
import pytest

CLI = Path(__file__).parents[3] / "trustgraph-cli" / "trustgraph" / "cli"


def _load_module(name):
    """Execute a doc-embeds CLI module without its top-level entry point."""
    source = (CLI / f"{name}.py").read_text()
    tree = ast.parse(source)
    body = [
        node for node in tree.body
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.ClassDef,
                             ast.FunctionDef, ast.AsyncFunctionDef, ast.Assign))
    ]
    module = types.ModuleType(name)
    exec(compile(ast.Module(body=body, type_ignores=[]), name, "exec"),
         module.__dict__)
    return module


@pytest.fixture
def load_de_mod():
    return _load_module("load_doc_embeds")


@pytest.fixture
def save_de_mod():
    return _load_module("save_doc_embeds")


def _core(tmp_path, messages):
    path = tmp_path / "core.msgpack"
    with open(path, "wb") as f:
        for msg in messages:
            f.write(msgpack.packb(msg, use_bin_type=True))
    return path


def _entry(doc_id="doc-1"):
    return ["de", {"m": {"i": doc_id, "m": [], "c": "default"},
                   "c": [{"c": "chunk", "v": [[0.1, 0.2]]}]}]


class TestLoader:
    """loader() reads the core file and feeds the queue."""

    async def test_corrupt_message_is_reported(self, load_de_mod, tmp_path):
        """A body that is not valid msgpack must not look like end of file."""
        path = tmp_path / "core.msgpack"
        path.write_bytes(msgpack.packb(_entry()) + b"\xc1\xc1\xc1")

        running = load_de_mod.Running()
        queue = asyncio.Queue(maxsize=10)

        with pytest.raises(Exception) as excinfo:
            await load_de_mod.loader(running, queue, str(path), "msgpack", None)

        assert not isinstance(excinfo.value, msgpack.exceptions.OutOfData)

    async def test_end_of_stream_stops_the_loader(self, load_de_mod, tmp_path):
        """Regression guard: passes with and without the fix."""
        path = _core(tmp_path, [_entry("a"), _entry("b")])

        running = load_de_mod.Running()
        queue = asyncio.Queue(maxsize=10)

        await asyncio.wait_for(
            load_de_mod.loader(running, queue, str(path), "msgpack", None), 5
        )

        assert queue.qsize() == 3
        assert queue.get_nowait()["m"]["i"] == "a"
        assert queue.get_nowait()["m"]["i"] == "b"
        assert queue.get_nowait() is None

    async def test_a_full_queue_does_not_lose_messages(self, load_de_mod,
                                                       tmp_path):
        """Regression guard: the put retry loop still waits for room."""
        path = _core(tmp_path, [_entry("a")])

        running = load_de_mod.Running()
        queue = asyncio.Queue(maxsize=1)
        filler = object()
        queue.put_nowait(filler)
        drained = []

        async def consumer():
            await asyncio.sleep(1.2)
            while True:
                item = await queue.get()
                drained.append(item)
                if item is None:
                    return

        await asyncio.wait_for(
            asyncio.gather(
                load_de_mod.loader(running, queue, str(path), "msgpack", None),
                consumer(),
            ),
            10,
        )

        assert drained[0] is filler
        assert drained[1]["m"]["i"] == "a"
        assert drained[2] is None

    async def test_a_put_failure_is_not_retried_forever(self, load_de_mod,
                                                        tmp_path, monkeypatch):
        """Anything other than a timeout on put() must surface."""
        path = _core(tmp_path, [_entry("a")])
        real_wait_for = asyncio.wait_for
        calls = []

        async def failing_wait_for(aw, timeout):
            calls.append(timeout)
            aw.close()
            await asyncio.sleep(0)
            if len(calls) > 3:
                return await real_wait_for(asyncio.sleep(0), timeout)
            raise RuntimeError("queue is broken")

        monkeypatch.setattr(load_de_mod.asyncio, "wait_for", failing_wait_for)

        running = load_de_mod.Running()
        with pytest.raises(RuntimeError, match="queue is broken"):
            await real_wait_for(
                load_de_mod.loader(
                    running, asyncio.Queue(maxsize=10), str(path), "msgpack",
                    None,
                ),
                5,
            )
        assert len(calls) == 1


class TestLoadDe:
    """load_de() drains the queue onto the websocket."""

    async def test_a_queue_failure_is_not_retried_forever(self, load_de_mod,
                                                          monkeypatch):
        real_wait_for = asyncio.wait_for
        calls = []

        async def failing_wait_for(aw, timeout):
            calls.append(timeout)
            aw.close()
            await asyncio.sleep(0)
            if len(calls) > 3:
                return None
            raise RuntimeError("queue is broken")

        monkeypatch.setattr(load_de_mod.asyncio, "wait_for", failing_wait_for)
        monkeypatch.setattr(load_de_mod.aiohttp, "ClientSession",
                            _fake_session_factory([]))

        running = load_de_mod.Running()
        with pytest.raises(RuntimeError, match="queue is broken"):
            await real_wait_for(
                load_de_mod.load_de(running, asyncio.Queue(), "ws://test/"), 5
            )
        assert len(calls) == 1


class TestOutput:
    """output() writes queued messages to the core file."""

    async def test_a_queue_failure_is_not_retried_forever(self, save_de_mod,
                                                          tmp_path,
                                                          monkeypatch):
        real_wait_for = asyncio.wait_for
        calls = []

        async def failing_wait_for(aw, timeout):
            calls.append(timeout)
            aw.close()
            await asyncio.sleep(0)
            if len(calls) > 3:
                # Escape hatch so a swallowed error cannot hang the suite.
                running.stop()
                return _entry("escape")
            raise RuntimeError("queue is broken")

        running = save_de_mod.Running()
        monkeypatch.setattr(save_de_mod.asyncio, "wait_for", failing_wait_for)

        path = tmp_path / "out.msgpack"
        with pytest.raises(RuntimeError, match="queue is broken"):
            await real_wait_for(
                save_de_mod.output(running, asyncio.Queue(), str(path),
                                   "msgpack"),
                10,
            )
        assert len(calls) == 1

    async def test_queued_messages_are_written(self, save_de_mod, tmp_path):
        """Regression guard: the timeout path still loops."""
        running = save_de_mod.Running()
        queue = asyncio.Queue()
        queue.put_nowait(_entry("a"))
        path = tmp_path / "out.msgpack"

        async def stop_soon():
            await asyncio.sleep(1.2)
            running.stop()

        await asyncio.gather(
            save_de_mod.output(running, queue, str(path), "msgpack"),
            stop_soon(),
        )

        unpacker = msgpack.Unpacker(open(path, "rb"), raw=False)
        assert unpacker.unpack()[1]["m"]["i"] == "a"
        assert save_de_mod.de_counts == 1


class TestFetchDe:
    """fetch_de() reads the websocket and queues what it finds."""

    async def test_a_socket_failure_is_not_retried_forever(self, save_de_mod,
                                                           monkeypatch):
        real_wait_for = asyncio.wait_for
        calls = []

        running = save_de_mod.Running()

        async def failing_wait_for(aw, timeout):
            calls.append(timeout)
            aw.close()
            await asyncio.sleep(0)
            if len(calls) > 3:
                # Escape hatch so a swallowed error cannot hang the suite.
                running.stop()
                return _FakeMessage()
            raise RuntimeError("socket is broken")

        monkeypatch.setattr(save_de_mod.asyncio, "wait_for", failing_wait_for)
        monkeypatch.setattr(save_de_mod.aiohttp, "ClientSession",
                            _fake_session_factory([]))

        with pytest.raises(RuntimeError, match="socket is broken"):
            await real_wait_for(
                save_de_mod.fetch_de(running, asyncio.Queue(), None,
                                     "ws://test/"),
                10,
            )
        assert len(calls) == 1


class _FakeMessage:
    """A websocket message of no interest to fetch_de."""
    type = None


def _fake_session_factory(messages):
    """Stand in for aiohttp.ClientSession().ws_connect() with no network."""

    class FakeWs:
        def __init__(self):
            self.sent = []

        async def send_json(self, msg):
            self.sent.append(msg)

        async def receive(self):
            if messages:
                return messages.pop(0)
            await asyncio.sleep(3600)

    class FakeConnect:
        async def __aenter__(self):
            return FakeWs()

        async def __aexit__(self, *exc):
            return False

    class FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        def ws_connect(self, url):
            return FakeConnect()

    return lambda *a, **k: FakeSession()
