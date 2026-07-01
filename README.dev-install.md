# TrustGraph Developer Install Guide

A guided installer that gets TrustGraph running locally in a single
command. It detects your hardware, recommends an LLM backend, installs
missing prerequisites, runs the test suite, generates a compose deployment,
starts the stack, and opens the Workbench UI.

> **macOS only.** This installer has only been tested on macOS. If you are
> on Linux or Windows, use the standard docker-compose / podman-compose
> installation instructions instead.

## Quick start

```bash
./install_trustgraph.sh
```

The installer walks you through each step interactively. When it finishes,
the Workbench UI opens at `http://localhost:8888` and the API gateway is
available at `http://localhost:8088/`.

## Prerequisites

The installer checks for these and offers to install any that are missing
(via Homebrew):

- **Python 3** with venv support
- **Node.js / npx** (drives the `@trustgraph/config` deployment generator)
- **Docker** (with Compose) or **Podman** (with podman-compose)
- **curl** and **unzip**
- **Ollama** (only if you choose local LLMs)

The installer can also launch Docker Desktop or the Ollama app for you if
they are installed but not running.

## What the installer does

1. **Detects hardware** -- OS, architecture, CPU cores, memory, and GPU.
2. **Recommends an LLM mode** -- `ollama` for machines with >= 16 GB RAM and
   a GPU or >= 8 cores; `openai` otherwise.
3. **Collects configuration** -- API key, LLM provider, model choices,
   install directory. Answers are saved to
   `<install-dir>/trustgraph-installer.env` and reused on subsequent runs.
4. **Checks and installs prerequisites** -- Python, Node/npx, Docker or
   Podman, Ollama (if selected).
5. **Downloads Ollama models** (if using Ollama) -- chat model
   (`granite4:350m` by default) and embeddings model (`mxbai-embed-large`).
6. **Creates a Python venv** and installs the local TrustGraph packages into
   it, along with NLTK data and tiktoken caches.
7. **Runs the full pytest suite** against the local source tree.
8. **Runs `npx @trustgraph/config`** -- the existing interactive config
   wizard that produces a `deploy.zip` with a compose file.
9. **Starts the compose stack** and waits for the API gateway to respond.
10. **Bootstraps IAM** and verifies the API key authenticates.
11. **Opens the Workbench UI** in your default browser.

## Command-line options

| Option | Description |
|---|---|
| `--install-dir PATH` | Directory for deployment files (default: `./trustgraph-deploy`) |
| `--api-url URL` | API gateway URL for health checks (default: `http://localhost:8088/`) |
| `--ui-url URL` | Workbench UI URL to open (default: `http://localhost:8888`) |
| `--use-existing-compose FILE` | Skip config generation and start this compose file directly |
| `--skip-tests` | Do not run the pytest suite |
| `--no-launch` | Do not open the Workbench UI at the end |
| `--non-interactive` | Accept all defaults without prompting |
| `--yes` | Auto-accept confirmation prompts |
| `--fresh` | Remove installer-managed files before generating a new deployment |
| `--remove-all` | Uninstall: stop containers, remove compose volumes, delete installer files |
| `--dry-run` | Print detected hardware and planned defaults, then exit |
| `-h`, `--help` | Show the built-in help text |

## Environment variables

These override the interactive prompts when set:

| Variable | Purpose |
|---|---|
| `TRUSTGRAPH_TOKEN` | Admin/bootstrap API key (must start with `tg_`) |
| `TRUSTGRAPH_URL` | API gateway URL |
| `TRUSTGRAPH_UI_URL` | Workbench UI URL |
| `OPENAI_TOKEN` | OpenAI-compatible API key |
| `OPENAI_BASE_URL` | OpenAI-compatible base URL |
| `OLLAMA_HOST` / `OLLAMA_BASE_URL` | Ollama service URL |
| `OLLAMA_MODEL` | Ollama chat model (default: `granite4:350m`) |
| `OLLAMA_EMBEDDINGS_MODEL` | Ollama embeddings model (default: `mxbai-embed-large`) |
| `TG_INSTALL_DIR` | Override the install directory |
| `TG_VENV_DIR` | Override the Python venv location |
| `TG_NLTK_DATA_DIR` | Override the NLTK data directory |
| `TIKTOKEN_CACHE_DIR` | Override the tiktoken cache directory |
| `TG_HEALTH_TIMEOUT` | Seconds to wait for the API gateway (default: 240) |

## Choosing an LLM mode

### OpenAI (or any OpenAI-compatible provider)

Best when you already have an API key or are running against a remote
endpoint. The installer asks for a base URL and an API key.

```bash
OPENAI_TOKEN=sk-... ./install_trustgraph.sh
```

### Ollama (local models)

Best on machines with enough RAM to run a small model. The installer detects
locally installed Ollama models and offers to pull missing ones. It uses
`host.docker.internal` so the Docker containers can reach the host-side
Ollama service.

```bash
./install_trustgraph.sh   # choose "ollama" when prompted
```

### None

Start the platform without an LLM. Agent and RAG features will not work
until you configure one later through the Workbench.

## Saved answers and re-running

The installer saves your answers to
`<install-dir>/trustgraph-installer.env`. On the next run it loads those
answers as defaults, so you can re-run with a single Enter through each
prompt.

To start completely fresh:

```bash
./install_trustgraph.sh --fresh
```

This stops any running containers (keeping Docker volumes), removes
installer-managed files, and re-runs the full flow.

## Using an existing compose file

If you already have a compose file from the config tool or another source:

```bash
./install_trustgraph.sh --use-existing-compose path/to/docker-compose.yaml
```

This skips the config wizard and `npx` prerequisite check, and goes straight
to starting the stack.

## Non-interactive / CI usage

```bash
TRUSTGRAPH_TOKEN=tg_my-token \
OPENAI_TOKEN=sk-... \
./install_trustgraph.sh --non-interactive --yes --skip-tests
```

In non-interactive mode the installer uses defaults for every prompt. Pair
with `--yes` to auto-accept confirmation prompts and `--skip-tests` if you
want a faster run.

## Dry run

Preview what the installer would do without making any changes:

```bash
./install_trustgraph.sh --dry-run
```

This prints the detected hardware, recommended LLM mode, and planned
install paths, then exits.

## Uninstalling

```bash
./install_trustgraph.sh --remove-all
```

This stops containers, removes compose-managed volumes, and deletes
installer-managed files (venv, deploy output, logs, saved answers). It does
**not** remove Docker/Podman itself, container images, Ollama, or Ollama
models.

## Troubleshooting

### Logs

All long-running operations write logs to `<install-dir>/logs/`. Key files:

- `pytest.log` -- test suite output
- `compose-up.log` -- docker compose output
- `iam-bootstrap.log` -- IAM bootstrap output
- `ollama-pull-*.log` -- Ollama model downloads
- `pip-*.log` -- Python package installs
- `brew-install-*.log` -- Homebrew installs

### API key rejected after reinstall

If the API gateway returns 401/403 with your saved key, the compose volumes
likely contain IAM data from a previous install with a different key. Run:

```bash
./install_trustgraph.sh --remove-all
./install_trustgraph.sh
```

This clears the old volumes and starts fresh.

### Ollama not reachable from containers

The Ollama base URL should use `host.docker.internal` instead of
`localhost` so that containers running in Docker Desktop can reach the
host-side Ollama service. The installer sets this automatically; if you
override `OLLAMA_HOST`, make sure the URL is reachable from inside the
container network.

### Docker daemon not running

The installer detects Docker Desktop and offers to start it. If that
doesn't work, start Docker Desktop manually and re-run the installer.
