
# ----------------------------------------------------------------------------
# Build an AI container.  This does the torch install which is huge, and I
# like to avoid re-doing this.
# ----------------------------------------------------------------------------

FROM docker.io/fedora:40 AS ai

ENV PIP_BREAK_SYSTEM_PACKAGES=1

RUN dnf install -y python3 python3-pip python3-wheel python3-aiohttp \
    python3-rdflib

RUN pip3 install torch --index-url https://download.pytorch.org/whl/cpu

RUN pip3 install anthropic boto3 cohere openai google-cloud-aiplatform langchain langchain-core \
    langchain-huggingface langchain-text-splitters langchain-community \
    pymilvus sentence-transformers transformers huggingface-hub \
    pulsar-client && \
    pip3 cache purge

# ----------------------------------------------------------------------------
# Build a container which contains the built Python package.  The build
# creates a bunch of left-over cruft, a separate phase means this is only
# needed to support package build
# ----------------------------------------------------------------------------

FROM ai AS build

env PACKAGE_VERSION=0.0.0

COPY setup.py /root/build/
COPY README.md /root/build/
COPY scripts/ /root/build/scripts/
COPY trustgraph/ root/build/trustgraph/

RUN (cd /root/build && pip3 wheel -w /root/wheels --no-deps .)

# ----------------------------------------------------------------------------
# Finally, the target container.  Start with base and add the package.
# ----------------------------------------------------------------------------

FROM ai

COPY --from=build /root/wheels /root/wheels

RUN pip3 install /root/wheels/trustgraph-* && \
    pip3 cache purge && \
    rm -rf /root/wheels

WORKDIR /

CMD sleep 1000000

