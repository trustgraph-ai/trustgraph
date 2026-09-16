---
layout: default
title: "Offline Invocation / HuggingFace Authentication Technical Specification"
parent: "Tech Specs"
---

# Offline Invocation / HuggingFace Authentication Technical Specification

## Overview

Several TrustGraph containers download machine-learning models at startup,
primarily from HuggingFace Hub. This creates two operational problems:

1. **Rate-limiting in shared environments**: Organisations with many
   unauthenticated HuggingFace users hit bandwidth limits, causing
   intermittent startup failures.
2. **Air-gapped / restricted networks**: Environments with no direct
   internet access cannot pull models at all.

The downloads are not performed by TrustGraph code directly -- they are
triggered by third-party libraries (sentence-transformers, fastembed,
flashrank, docling) that TrustGraph depends on.  TrustGraph selects only
components whose model-download behaviour is well understood and
transparent, but the download mechanics are managed by those libraries
rather than by TrustGraph itself.  This means the solution must work at
the environment and container level rather than through application code
changes.

This specification describes a unified approach to HuggingFace
authentication and fully offline model provisioning across all affected
containers.

## Scope

### In Scope

This specification covers containers that implicitly download small
utility models (embeddings, rerankers, document-processing pipelines)
from HuggingFace Hub as a side-effect of startup or first use.  These
downloads are often invisible to operators and are the primary source of
unexpected network dependencies.

### Out of Scope: LLM Inference

Large Language Model serving is **not** addressed by this specification.
TrustGraph already supports fully offline LLM inference through
self-hosted backends such as vLLM, Ollama, and other local serving
frameworks.  When an operator deploys one of these backends, the LLM
weights are managed explicitly -- downloaded ahead of time, served from
local storage, and accessed by TrustGraph over a local network endpoint.
There is no implicit runtime download from HuggingFace.

Cloud-hosted LLM providers (Vertex AI, Bedrock, OpenAI-compatible APIs)
are network-dependent by nature but do not interact with HuggingFace Hub,
so they are unaffected by the problems described here.

In short, LLM inference already has well-understood offline deployment
paths and does not suffer from the unauthenticated-download / rate-limit
problems that motivate this specification.

### Discussion: Why Utility Models Are Different from LLMs

LLM serving is an explicit, high-visibility deployment decision.
Operators choose a backend, download multi-gigabyte weights, configure
GPU resources, and expose an inference endpoint.  The model acquisition
step is unavoidable and obvious.

Utility models are the opposite.  An embeddings library quietly fetches
an 80 MB model on first call; a reranker downloads a 50 MB checkpoint
into `/tmp`; a document converter pulls layout-detection weights the
first time it sees a PDF.  These downloads are:

- **Invisible**: they happen inside library initialisation code with no
  operator action required.
- **Unauthenticated**: the libraries default to anonymous HuggingFace
  Hub access.
- **Unreliable in shared environments**: anonymous requests share a
  global rate-limit pool, so a deployment that worked yesterday can fail
  today because other tenants on the same network consumed the quota.
- **Blocking in air-gapped networks**: unlike LLM backends, there is no
  "point at a local server" option -- the libraries expect to reach
  HuggingFace Hub directly.

This asymmetry is why utility-model provisioning needs its own solution
while LLM serving does not.

## Goals

- **Authenticated downloads**: Allow operators to supply a HuggingFace
  token so that downloads are attributed to a paid/authenticated account,
  avoiding anonymous rate limits.
- **Pre-baked container images**: Every model required at runtime is
  already present in the published container image, eliminating startup
  downloads for the default configuration.
- **Offline mode**: Provide a supported, tested path for running
  TrustGraph with no outbound internet access.
- **Custom model support**: Operators who configure a non-default model
  can still pre-cache it, either at image build time or via a volume
  mount.
- **No behavioural change for online users**: The default experience for
  users with internet access must remain unchanged.

## Background

### Current State

Three container images download HuggingFace-hosted models:

| Container | Image | Library | Default Model | Pre-baked? |
|-----------|-------|---------|---------------|------------|
| HF Embeddings | `Containerfile.hf` | `langchain-huggingface` / `sentence-transformers` | `all-MiniLM-L6-v2` | Yes |
| Flow (FastEmbed) | `Containerfile.flow` | `fastembed` (ONNX) | `sentence-transformers/all-MiniLM-L6-v2` | No |
| Flow (FlashRank) | `Containerfile.flow` | `flashrank` (ONNX) | `ms-marco-MiniLM-L-12-v2` | No |
| Docling | `Containerfile.docling` | `docling` / `transformers` | Layout + TableFormer pipeline models | No |

The HF Embeddings container already pre-downloads its default model
(`RUN hf download sentence-transformers/all-MiniLM-L6-v2`).  The other
containers rely on lazy download at first use.

### Current Limitations

- **No HF token support**: No container accepts or forwards a
  HuggingFace API token; all downloads are anonymous.
- **Inconsistent pre-caching**: Only `Containerfile.hf` bakes in its
  default model.  FastEmbed, FlashRank, and Docling models are fetched on
  first request.
- **No offline enforcement**: The environment variables `HF_HUB_OFFLINE=1`
  and `TRANSFORMERS_OFFLINE=1` are documented in draft notes but not set
  or tested in any published container.
- **Cache path fragility**: FastEmbed and FlashRank use different default
  cache locations (`~/.cache/fastembed`, `/tmp/flashrank`, etc.) that are
  not explicitly pinned in container builds.

## Technical Design

The work is structured in three phases, ordered by effort-to-value
ratio.  Each phase is independently shippable and useful on its own.

### Phase 1: Pre-load Models into Container Images

This is the quick win.  Pre-download default models at build time so
they are present in the published images, eliminating startup downloads
for the default configuration.

`Containerfile.hf` already does this for the HF embeddings model
(`RUN hf download sentence-transformers/all-MiniLM-L6-v2`).  Phase 1
extends the same pattern to the flow and docling containers.

**Changes to `Containerfile.flow`:**

```dockerfile
# Pin cache directories so they are deterministic and inspectable
ENV FASTEMBED_CACHE_PATH=/opt/models/fastembed

# Pre-download default FastEmbed model
RUN python -c "\
from fastembed import TextEmbedding; \
TextEmbedding(model_name='sentence-transformers/all-MiniLM-L6-v2')"

# Pre-download default FlashRank model
RUN python -c "\
from flashrank import Ranker; \
Ranker(model_name='ms-marco-MiniLM-L-12-v2')"
```

**Changes to `Containerfile.docling`:**

```dockerfile
# Pre-initialise Docling PDF pipeline to cache model weights
RUN python -c "\
from docling.document_converter import DocumentConverter, InputFormat; \
converter = DocumentConverter(); \
converter.initialize_pipeline(InputFormat.PDF)"
```

Docling's OCR is handled by RapidOCR, whose ONNX models are already
shipped inside the pip package
(`site-packages/rapidocr/models/`) and do not require a separate
download.  The `initialize_pipeline` call caches the layout detection
and table structure models that Docling fetches from HuggingFace Hub.
Some models may be lazy-loaded only when triggered by specific document
content (e.g. tables); further testing with representative PDFs is
needed to confirm the full set of models is captured by this step.

Pre-caching must happen in (or be copied into) the final image stage to
survive multi-stage builds.

**Cache directory pinning:**

| Library | Environment Variable | Container Path |
|---------|---------------------|----------------|
| FastEmbed | `FASTEMBED_CACHE_PATH` | `/opt/models/fastembed` |
| FlashRank | (uses HF cache or `/tmp`) | `/opt/models/flashrank` |
| Docling | `HF_HOME` | `/root/.cache/huggingface` (default) |

**Cache-freshness behaviour:**

Pre-baking models into the image does not, by itself, prevent all
network access at runtime.  Each library handles cached models
differently:

| Library | Behaviour when model is cached locally |
|---------|----------------------------------------|
| **FastEmbed** | Uses `huggingface_hub.snapshot_download()`, which checks the model's ETag against HuggingFace Hub on every load.  If the Hub is unreachable, it waits for the ETag timeout (default 10 seconds) before falling back to the local copy.  A newer revision on the Hub will be downloaded, replacing the pre-baked version. |
| **FlashRank** | Simple directory-existence check.  If the model directory exists locally, it is used immediately with no network call.  Safe for offline use out of the box. |
| **LangChain-HF** (sentence-transformers, used in `Containerfile.hf`) | Same ETag-checking behaviour as FastEmbed -- phones home on every load via `huggingface_hub`. |

This means that for FastEmbed and the HF embeddings container,
pre-baking is necessary but not sufficient for offline operation.
Without `HF_HUB_OFFLINE=1`, those libraries will still attempt a
network call on every model load, adding a 10-second timeout penalty per
model if HuggingFace Hub is unreachable.  In shared environments without
offline mode enabled, a newer model revision pushed to HuggingFace could
silently replace the pre-baked version.

The `HF_HUB_ETAG_TIMEOUT` environment variable can reduce the timeout
(e.g. to 0 for fail-fast behaviour), but setting `HF_HUB_OFFLINE=1` is
the recommended approach for reliable offline operation.

**Offline enforcement:**

With default models pre-loaded, the flow container can run fully offline
by setting two environment variables at runtime:

```
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1
```

These are **not** baked into the image -- online users can still download
non-default models at runtime.  For air-gapped deployments, a Docker
Compose override or Helm values file sets them globally:

```yaml
# docker-compose.offline.yml (partial)
services:
  flow:
    environment:
      - HF_HUB_OFFLINE=1
      - TRANSFORMERS_OFFLINE=1
```

**Custom / non-default models:**

Operators who configure a model other than the pre-baked default have
two options:

1. **Build a derived image** that pre-downloads the custom model:
   ```dockerfile
   FROM trustgraph/trustgraph-flow:latest
   RUN python -c "from fastembed import TextEmbedding; \
       TextEmbedding(model_name='BAAI/bge-small-en-v1.5')"
   ```

2. **Volume-mount a pre-populated cache directory** into the container at
   the appropriate cache path (e.g. `/opt/models/fastembed`).

Both approaches work with `HF_HUB_OFFLINE=1`.

**Processor code:**

The Python processors (`hf.py`, `fastembed/processor.py`,
`flashrank/processor.py`) already implement lazy model loading with
in-process caching.  No application code changes are needed -- the
pre-caching and offline enforcement operate entirely at the library /
environment level.

Processors should emit a clear log message when model loading fails in
offline mode, so operators can diagnose missing models:

```python
try:
    self.embeddings = HuggingFaceEmbeddings(model_name=model_name)
except Exception as e:
    if os.environ.get("HF_HUB_OFFLINE") == "1":
        logger.error(
            "Model %s not found in local cache and HF_HUB_OFFLINE=1. "
            "Pre-download the model or disable offline mode.",
            model_name,
        )
    raise
```

### Phase 2: Verify Fully Offline Docling Operation

Phase 1 adds the basic `initialize_pipeline` pre-cache to the Docling
image.  Phase 2 validates that this is sufficient for fully offline
operation and addresses any gaps.

Some Docling models may be lazy-loaded only when specific document
features are encountered (e.g. TableFormer weights when a table is
detected).  The `initialize_pipeline` call may not trigger all of these.

**Validation steps:**

- Run the Docling container with `--network none` and process a
  representative set of PDFs (with tables, images, scanned pages).
- Compare the HF cache contents before and after processing to identify
  any models that were not captured by `initialize_pipeline`.
- If additional models are needed, add further pre-download steps to the
  Containerfile or investigate whether Docling provides a more complete
  pre-cache API.
- If certain features cannot be reliably pre-cached, consider disabling
  them in an offline profile (e.g. turning off table structure detection)
  and document the trade-off.

### Phase 3: HuggingFace Token Support

For environments that have internet access but hit anonymous rate limits,
HuggingFace token injection provides authenticated downloads with
significantly higher rate limits.

HuggingFace libraries honour the `HF_TOKEN` environment variable.  When
set, all Hub API calls use authenticated requests.

**Build-time token injection:**

The token must not be baked into image layers.  Use Docker BuildKit
secret mounts:

```dockerfile
RUN --mount=type=secret,id=hf_token \
    HF_TOKEN=$(cat /run/secrets/hf_token) \
    hf download sentence-transformers/all-MiniLM-L6-v2
```

**Runtime token injection:**

Operators pass `HF_TOKEN` via environment variable, using container
orchestration secrets (Kubernetes Secrets, Docker secrets) rather than
plain-text environment files:

```bash
docker run -e HF_TOKEN=hf_xxx ...
```

**Changes required:**

- Accept `HF_TOKEN` as an optional environment variable in all
  containers that interact with HuggingFace Hub.
- Pass `HF_TOKEN` as a Docker build secret so that build-time model
  prefetch steps can authenticate.
- Document the token injection in deployment guides.

## Security Considerations

- **Token handling**: The `HF_TOKEN` must not be baked into image layers.
  Use Docker `--secret` mounts for build-time access.  At runtime, the
  token is passed via environment variable, consistent with standard
  HuggingFace practice.  Operators should use container orchestration
  secrets (Kubernetes Secrets, Docker secrets) rather than plain-text
  environment files.
- **Model integrity**: Pre-cached models are downloaded during a
  controlled build step, which is auditable.  Offline mode ensures no
  unexpected model substitution at runtime.
- **Network policy**: Air-gapped deployments can apply network policies
  that block egress to `huggingface.co` as a defence-in-depth measure
  alongside `HF_HUB_OFFLINE=1`.

## Performance Considerations

- **Image size**: Pre-baking models increases image size.  The default
  embeddings model (`all-MiniLM-L6-v2`) is ~80 MB; FlashRank's
  `ms-marco-MiniLM-L-12-v2` is ~50 MB; Docling pipeline models are
  ~200-400 MB.  For context, current image sizes are:

  | Image | Size |
  |-------|------|
  | `trustgraph-ui` | 101 MB |
  | `trustgraph-mcp` | 344 MB |
  | `trustgraph-flow` | 978 MB |
  | `trustgraph-enterprise` | 971 MB |
  | `trustgraph-docling` | 2.37 GB |

  Adding ~130 MB of utility models to the flow image (~13% growth) is
  modest relative to its existing size.  The docling image is already
  the largest by far at 2.37 GB; pre-baking its pipeline models adds
  proportionally less.  In both cases the trade-off is clearly
  favourable: eliminating a flaky, invisible network dependency at
  startup is worth a fraction of the image size that operators are
  already pulling.
- **Startup time**: Eliminates the first-request model download penalty,
  which can be 30-120 seconds depending on network conditions.
- **Multi-stage build overhead**: Model pre-cache layers must survive the
  final `COPY --from=build` stage, which may require restructuring some
  Containerfiles to cache models in the final stage rather than the build
  stage.

## Testing Strategy

- **Build verification**: CI builds each container image and asserts that
  model cache directories exist and contain expected files.
- **Offline smoke test**: Run each container with `--network none` and
  verify that the default model loads without error.
- **Authenticated build test**: Build with a test HF token (via
  `--secret`) and verify the build log shows authenticated access.
- **Custom model test**: Build a derived image with a non-default model,
  run offline, and verify it serves embeddings / reranking correctly.

## Migration Plan

All phases are additive with no breaking behaviour.

1. **Phase 1 -- Pre-load models into container images**: Dockerfile-only
   changes to `Containerfile.flow` (FastEmbed + FlashRank) and
   `Containerfile.docling` (pipeline initialisation).  Pin cache
   directories, add pre-download steps.  Ship a
   `docker-compose.offline.yml` overlay.  Add offline-aware error
   logging to processors.  This phase has no dependencies and can ship
   immediately.
2. **Phase 2 -- Verify fully offline Docling operation**: Test the
   Docling image from Phase 1 with `--network none` against
   representative PDFs.  Identify and pre-cache any lazy-loaded models
   not covered by `initialize_pipeline`.
3. **Phase 3 -- HuggingFace token support**: Add `HF_TOKEN` passthrough
   to Containerfiles (BuildKit secret mount) and document in deployment
   guides.  Independent of phases 1 and 2 but lower priority since
   pre-caching solves the immediate problem.

## Open Questions

- Should the published container images set `HF_HUB_OFFLINE=1` by
  default (fully offline-by-default) or leave it unset (online-by-default
  with offline as opt-in)?  Online-by-default is less surprising for new
  users; offline-by-default is more secure.
- Should we provide a standalone model-download utility image or script
  that operators can run to populate a shared volume with arbitrary
  models, rather than requiring derived images?
- Are there additional containers beyond HF Embeddings, Flow, and
  Docling that download utility models at runtime?
- What is the support policy for FastEmbed / FlashRank cache format
  changes across library version upgrades?

## References

- [HuggingFace Hub offline mode](https://huggingface.co/docs/huggingface_hub/guides/manage-cache#offline-mode)
- [Docker BuildKit secrets](https://docs.docker.com/build/building/secrets/)
- Existing pre-cache pattern: `containers/Containerfile.hf:31`
- Draft offline notes: `#README.offline#`
