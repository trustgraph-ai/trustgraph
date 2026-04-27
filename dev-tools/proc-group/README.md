# proc-group — run TrustGraph as a single process

A dev-focused alternative to the per-container deployment. Instead of 30+
containers each running a single processor, `processor-group` runs all the
processors as asyncio tasks inside one Python process, sharing the event
loop, Prometheus registry, and (importantly) resources on your laptop.

This is **not** for production. Scale deployments should keep using
per-processor containers — one failure bringing down the whole process,
no horizontal scaling, and a single giant log are fine for dev and a
bad idea in prod.

## What this directory contains

- `group.yaml` — the group runner config. One entry per processor, each
  with the dotted class path and a params dict. Defaults (pubsub backend,
  rabbitmq host, log level) are pulled in per-entry with a YAML anchor.
- `README.md` — this file.

## Prerequisites

Install the TrustGraph packages into a venv:

```
pip install trustgraph-base trustgraph-flow trustgraph-unstructured
```

`trustgraph-base` provides the `processor-group` endpoint. The others
provide the processor classes that `group.yaml` imports at runtime.
`trustgraph-unstructured` is only needed if you want `document-decoder`
(the `universal-decoder` processor).

## Running it

Start infrastructure (cassandra, qdrant, rabbitmq, garage, observability
stack) with a working compose file. These aren't packable into the group -
they're third-party services.  You may be able to run these as standalone
services.

To get Cassandra to be accessible from the host, you need to 
set a couple of environment variables:
```
      CASSANDRA_BROADCAST_ADDRESS: 127.0.0.1
      CASSANDRA_LISTEN_ADDRESS: 127.0.0.1
```
and also set `network: host`.  Then start services:

```
podman-compose up -d cassandra qdrant rabbitmq
podman-compose up -d garage garage-init
podman-compose up -d loki prometheus grafana
podman-compose up -d init-trustgraph
```

`init-trustgraph` is a one-shot that seeds config and the default flow
into cassandra/rabbitmq.  Don't leave too long a delay between starting
`init-trustgraph` and running the processor-group, because it needs to
talk to the config service.

Run the api-gateway separately — it's an aiohttp HTTP server, not an
`AsyncProcessor`, so the group runner doesn't host it:

Raise the file descriptor limit — 30+ processors sharing one process
open far more sockets than the default 1024 allows:

```
ulimit -n 65536
```

Then start the group from a terminal:

```
processor-group -c group.yaml --no-loki-enabled
```

You'll see every processor's startup messages interleaved in one log.
Each processor has a supervisor that restarts it independently on
failure, so a transient crash (or a dependency that isn't ready yet)
only affects that one processor — siblings keep running and the failing
one self-heals on the next retry.

Finally when everything is running you can start the API gateway from
its own terminal:

```
api-gateway \
    --pubsub-backend rabbitmq --rabbitmq-host localhost \
    --loki-url http://localhost:3100/loki/api/v1/push \
    --no-metrics
```



## When things go wrong

- **"Too many open files"** — raise `ulimit -n` further. 65536 is
  usually plenty but some workflows need more.
- **One processor failing repeatedly** — look for its id in the log. The
  supervisor will log each failure before restarting. Fix the cause
  (missing env var, unreachable dependency, bad params) and the
  processor self-heals on the next 4-second retry without restarting
  the whole group.
- **Ctrl-C leaves the process hung** — the pika and cassandra drivers
  spawn non-cooperative threads that asyncio can't cancel. Use Ctrl-\
  (SIGQUIT) to force-kill. Not a bug in the group runner, just a
  limitation of those libraries.

## Environment variables

Processors that talk to external LLMs or APIs read their credentials
from env vars, same as in the per-container deployment:

- `OPENAI_TOKEN`, `OPENAI_BASE_URL` — for `text-completion` /
  `text-completion-rag`

Export whatever your particular `group.yaml` needs before running.

