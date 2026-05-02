#!/usr/bin/env python3
"""
WebSocket smoke / load test that hammers a TrustGraph gateway with a
mix of `embeddings`, `graph-embeddings`, and `triples` queries while
keeping a target number of in-flight requests at all times.

Useful for reproducing the "worker hangs after a while, all subsequent
requests time out" failure mode — leaves enough load on the system to
saturate worker concurrency and reports per-service success/timeout
rates and latency distributions over time.

Usage:
    smoke_ws_queries.py --flow onto-rag --duration 120 --concurrency 20

Connects via /api/v1/socket using the first-frame auth protocol.
"""

import argparse
import asyncio
import json
import os
import random
import statistics
import sys
import time
import uuid
from collections import defaultdict
from typing import Any

import websockets


DEFAULT_TEXT = (
    "What caused the space shuttle to explode and what were the "
    "main factors leading to the disaster?"
)


class Stats:
    """Per-service rolling counters and latency samples."""

    def __init__(self) -> None:
        self.sent = 0
        self.ok = 0
        self.err = 0
        self.timeout = 0
        self.latencies_ms: list[float] = []

    def record_ok(self, latency_ms: float) -> None:
        self.ok += 1
        self.latencies_ms.append(latency_ms)

    def record_err(self) -> None:
        self.err += 1

    def record_timeout(self) -> None:
        self.timeout += 1

    def percentile(self, p: float) -> float:
        if not self.latencies_ms:
            return 0.0
        s = sorted(self.latencies_ms)
        idx = min(len(s) - 1, int(len(s) * p))
        return s[idx]

    def summary(self) -> str:
        if self.latencies_ms:
            mn = min(self.latencies_ms)
            mx = max(self.latencies_ms)
            mean = statistics.mean(self.latencies_ms)
            p50 = self.percentile(0.50)
            p95 = self.percentile(0.95)
            p99 = self.percentile(0.99)
            lat = (
                f"min={mn:.0f} mean={mean:.0f} p50={p50:.0f} "
                f"p95={p95:.0f} p99={p99:.0f} max={mx:.0f} ms"
            )
        else:
            lat = "no successful samples"
        return (
            f"sent={self.sent} ok={self.ok} err={self.err} "
            f"timeout={self.timeout} | {lat}"
        )


class WSClient:
    """Thin async websocket client with first-frame auth and a shared
    reader task that demuxes responses to per-request asyncio queues."""

    def __init__(
        self, url: str, token: str | None, workspace: str,
        ping_timeout: int,
    ) -> None:
        self.url = url
        self.token = token
        self.workspace = workspace
        self.ping_timeout = ping_timeout
        self._ws: Any = None
        self._pending: dict[str, asyncio.Queue] = {}
        self._reader_task: asyncio.Task | None = None
        self._closed = asyncio.Event()

    async def connect(self) -> None:
        ws_url = self.url.rstrip("/") + "/api/v1/socket"
        if ws_url.startswith("http://"):
            ws_url = "ws://" + ws_url[len("http://"):]
        elif ws_url.startswith("https://"):
            ws_url = "wss://" + ws_url[len("https://"):]
        elif not (
            ws_url.startswith("ws://") or ws_url.startswith("wss://")
        ):
            ws_url = "ws://" + ws_url

        self._ws = await websockets.connect(
            ws_url,
            ping_interval=20,
            ping_timeout=self.ping_timeout,
            max_size=64 * 1024 * 1024,
        )

        if self.token:
            # First-frame auth handshake.
            await self._ws.send(json.dumps({
                "type": "auth", "token": self.token,
            }))
            raw = await asyncio.wait_for(self._ws.recv(), timeout=10)
            resp = json.loads(raw)
            if resp.get("type") != "auth-ok":
                await self._ws.close()
                raise RuntimeError(f"auth failed: {resp}")
            if "workspace" in resp:
                # Server-resolved workspace overrides the user-supplied
                # one, mirroring AsyncSocketClient behaviour.
                self.workspace = resp["workspace"]
        else:
            print(
                "WARNING: no token provided — skipping auth handshake. "
                "Requests will be rejected unless the gateway is "
                "running without IAM enforcement.",
                file=sys.stderr,
            )

        self._reader_task = asyncio.create_task(self._reader())

    async def _reader(self) -> None:
        try:
            async for raw in self._ws:
                msg = json.loads(raw)
                rid = msg.get("id")
                if rid and rid in self._pending:
                    await self._pending[rid].put(msg)
        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            for q in list(self._pending.values()):
                try:
                    q.put_nowait({"error": {"message": str(e)}})
                except Exception:
                    pass
        finally:
            self._closed.set()

    async def request(
        self, service: str, flow: str | None, body: dict, timeout: float,
    ) -> tuple[dict | None, str | None, float]:
        """Send one request, await final response.

        Returns ``(response, error, latency_ms)``. ``response`` is None
        on error/timeout. ``error`` describes the failure category.
        """
        rid = str(uuid.uuid4())
        q: asyncio.Queue = asyncio.Queue()
        self._pending[rid] = q
        env = {
            "id": rid,
            "workspace": self.workspace,
            "service": service,
            "request": body,
        }
        if flow:
            env["flow"] = flow

        t0 = time.monotonic()
        try:
            await self._ws.send(json.dumps(env))
            while True:
                try:
                    msg = await asyncio.wait_for(q.get(), timeout=timeout)
                except asyncio.TimeoutError:
                    return None, "timeout", (time.monotonic() - t0) * 1000
                if "error" in msg and msg["error"]:
                    err = msg["error"]
                    err_msg = (
                        err.get("message") if isinstance(err, dict) else str(err)
                    )
                    return None, f"error: {err_msg}", (time.monotonic() - t0) * 1000
                if msg.get("complete"):
                    return msg.get("response"), None, (time.monotonic() - t0) * 1000
                # Otherwise an intermediate streaming chunk — keep waiting.
        finally:
            self._pending.pop(rid, None)

    async def close(self) -> None:
        if self._ws is not None:
            await self._ws.close()
        if self._reader_task is not None:
            try:
                await asyncio.wait_for(self._reader_task, timeout=2)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--url",
        default=os.getenv("TRUSTGRAPH_URL", "http://localhost:8088/"),
        help="Gateway URL (http or ws). Default: %(default)s",
    )
    p.add_argument(
        "--token",
        default=os.getenv("TRUSTGRAPH_TOKEN"),
        help="Auth token (or set TRUSTGRAPH_TOKEN). Optional — if "
             "omitted, the auth handshake is skipped (only works "
             "when the gateway is running without IAM enforcement).",
    )
    p.add_argument(
        "--workspace", default="default",
        help="Workspace. Default: %(default)s",
    )
    p.add_argument(
        "--flow", required=True,
        help="Flow id. Comma-separated for round-robin across flows "
             "(e.g. onto-rag,doc-rag).",
    )
    p.add_argument(
        "--duration", type=int, default=60,
        help="Test duration in seconds. Default: %(default)s",
    )
    p.add_argument(
        "--concurrency", type=int, default=15,
        help="Target in-flight request count. Default: %(default)s",
    )
    p.add_argument(
        "--services",
        default="embeddings,graph-embeddings,triples",
        help="Comma-separated services to exercise. "
             "Default: %(default)s",
    )
    p.add_argument(
        "--limit", type=int, default=3,
        help="limit for triples / graph-embeddings queries. "
             "Default: %(default)s",
    )
    p.add_argument(
        "--collection", default="default",
        help="Collection. Default: %(default)s",
    )
    p.add_argument(
        "--text", default=DEFAULT_TEXT,
        help="Text to embed for embeddings/seed.",
    )
    p.add_argument(
        "--vector-dim", type=int, default=384,
        help="Dimension of synthetic vector when --no-seed is used. "
             "Default: %(default)s",
    )
    p.add_argument(
        "--no-seed", action="store_true",
        help="Skip the embeddings warm-up call. Use a random vector "
             "for graph-embeddings queries instead.",
    )
    p.add_argument(
        "--request-timeout", type=float, default=30.0,
        help="Per-request timeout (seconds). Default: %(default)s",
    )
    p.add_argument(
        "--report-interval", type=float, default=5.0,
        help="How often to print stats (seconds). Default: %(default)s",
    )
    p.add_argument(
        "--ping-timeout", type=int, default=120,
        help="Websocket ping timeout. Default: %(default)s",
    )
    p.add_argument(
        "--seed", type=int, default=None,
        help="Random seed (for reproducibility).",
    )
    return p.parse_args()


async def seed_vector(
    client: WSClient, flow: str, text: str, timeout: float,
) -> list[float]:
    """Issue one embeddings request to obtain a real vector that
    later graph-embeddings calls can reuse."""
    resp, err, _ = await client.request(
        "embeddings", flow, {"texts": [text]}, timeout,
    )
    if err or not resp:
        raise RuntimeError(f"seed embeddings failed: {err or resp}")
    vectors = resp.get("vectors")
    if not vectors:
        raise RuntimeError(f"seed embeddings: no vectors in response: {resp}")
    return vectors[0]


def make_request_body(
    service: str, args: argparse.Namespace, vector: list[float],
) -> dict:
    if service == "embeddings":
        return {"texts": [args.text]}
    if service == "graph-embeddings":
        return {
            "vector": vector,
            "limit": args.limit,
            "collection": args.collection,
        }
    if service == "triples":
        return {
            "limit": args.limit,
            "collection": args.collection,
        }
    raise ValueError(f"Unknown service: {service}")


async def worker(
    name: int,
    client: WSClient,
    flows: list[str],
    services: list[str],
    args: argparse.Namespace,
    vector: list[float],
    stats: dict[str, Stats],
    in_flight: dict[str, int],
    stop_at: float,
) -> None:
    rng = random.Random((args.seed or 0) + name)
    while time.monotonic() < stop_at:
        svc = rng.choice(services)
        flow = rng.choice(flows)
        body = make_request_body(svc, args, vector)

        stats[svc].sent += 1
        in_flight[svc] += 1
        try:
            resp, err, lat = await client.request(
                svc, flow, body, args.request_timeout,
            )
            if err == "timeout":
                stats[svc].record_timeout()
            elif err:
                stats[svc].record_err()
            else:
                stats[svc].record_ok(lat)
        except Exception as e:
            stats[svc].record_err()
            print(f"worker {name}: unexpected {svc} exception: {e}",
                  file=sys.stderr)
        finally:
            in_flight[svc] -= 1


async def reporter(
    services: list[str],
    stats: dict[str, Stats],
    in_flight: dict[str, int],
    stop_at: float,
    interval: float,
) -> None:
    started = time.monotonic()
    last_sent = {s: 0 for s in services}
    while time.monotonic() < stop_at:
        await asyncio.sleep(interval)
        now = time.monotonic()
        elapsed = now - started
        total_inflight = sum(in_flight.values())
        print(
            f"\n[{elapsed:6.1f}s] in-flight={total_inflight} "
            f"per-svc={dict(in_flight)}"
        )
        for svc in services:
            s = stats[svc]
            delta = s.sent - last_sent[svc]
            rate = delta / interval
            last_sent[svc] = s.sent
            print(f"  {svc:20s} {rate:6.1f}/s | {s.summary()}")


async def run(args: argparse.Namespace) -> int:
    if args.seed is not None:
        random.seed(args.seed)

    services = [s.strip() for s in args.services.split(",") if s.strip()]
    flows = [f.strip() for f in args.flow.split(",") if f.strip()]
    valid = {"embeddings", "graph-embeddings", "triples"}
    bad = [s for s in services if s not in valid]
    if bad:
        print(f"ERROR: unknown service(s): {bad}. "
              f"Supported: {sorted(valid)}", file=sys.stderr)
        return 2

    client = WSClient(
        args.url, args.token, args.workspace, args.ping_timeout,
    )
    print(f"Connecting to {args.url} ...")
    await client.connect()
    print(f"Connected. workspace={client.workspace} flows={flows} "
          f"services={services} concurrency={args.concurrency} "
          f"duration={args.duration}s")

    if "graph-embeddings" in services and not args.no_seed:
        print("Seeding embedding vector ...")
        vector = await seed_vector(
            client, flows[0], args.text, args.request_timeout,
        )
        print(f"Got vector of length {len(vector)}")
    else:
        vector = [random.uniform(-1.0, 1.0) for _ in range(args.vector_dim)]

    stats: dict[str, Stats] = defaultdict(Stats)
    in_flight: dict[str, int] = defaultdict(int)
    for svc in services:
        stats[svc]  # initialise
        in_flight[svc] = 0

    stop_at = time.monotonic() + args.duration
    print(f"Starting load: {args.concurrency} workers for "
          f"{args.duration}s ...")

    workers = [
        asyncio.create_task(
            worker(
                i, client, flows, services, args, vector,
                stats, in_flight, stop_at,
            )
        )
        for i in range(args.concurrency)
    ]
    rep = asyncio.create_task(
        reporter(services, stats, in_flight, stop_at, args.report_interval)
    )

    try:
        await asyncio.gather(*workers)
    finally:
        rep.cancel()
        try:
            await rep
        except asyncio.CancelledError:
            pass

        print("\n=== Final results ===")
        any_failures = False
        for svc in services:
            s = stats[svc]
            print(f"  {svc:20s} {s.summary()}")
            if s.timeout > 0 or s.err > 0:
                any_failures = True

        await client.close()

    return 1 if any_failures else 0


def main() -> int:
    args = parse_args()
    try:
        return asyncio.run(run(args))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
