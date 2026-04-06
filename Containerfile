# --- STAGE 1: Build ---
FROM python:3.14-slim AS build

# Install build tools (Debian uses apt)
RUN apt-get update && apt-get install -y \
    build-essential \
    golang \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /root/wheels /root/build

# Build wheels
RUN pip wheel -w /root/wheels --no-deps gojsonnet

COPY trustgraph_configurator/ /root/build/trustgraph_configurator/
COPY pyproject.toml /root/build/pyproject.toml
COPY README.md /root/build/README.md

RUN (cd /root/build && pip wheel -w /root/wheels --no-deps .)

# --- STAGE 2: Runtime ---
FROM python:3.14-slim

# No need to install libstdc++ manually, it's included in python-slim
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# aiohttp and others will be pulled from PyPI or handled via wheels
COPY --from=build /root/wheels /root/wheels

# Install your wheels plus regular dependencies
RUN pip install --no-cache-dir /root/wheels/* aiohttp pyyaml tabulate && \
    rm -rf /root/wheels

CMD ["tg-config-svc"]
EXPOSE 8080

