
# ----------------------------------------------------------------------------
# Build an AI container.  This does the torch install which is huge, and I
# like to avoid re-doing this.
# ----------------------------------------------------------------------------

FROM docker.io/fedora:40 AS ai

ENV PIP_BREAK_SYSTEM_PACKAGES=1

RUN dnf install -y python3 python3-pip python3-wheel python3-aiohttp \
    python3-rdflib

RUN pip3 install torch --index-url https://download.pytorch.org/whl/cpu

RUN pip3 install anthropic boto3 cohere openai google-cloud-aiplatform ollama \
    langchain langchain-core langchain-huggingface langchain-text-splitters \
    langchain-community pymilvus sentence-transformers transformers \
    huggingface-hub pulsar-client cassandra-driver pyarrow pyyaml \
    neo4j tiktoken && \
    pip3 cache purge

# ----------------------------------------------------------------------------
# Build a container which contains the built Python packages.  The build
# creates a bunch of left-over cruft, a separate phase means this is only
# needed to support package build
# ----------------------------------------------------------------------------

FROM ai AS build

COPY trustgraph-base/ /root/build/trustgraph-base/
COPY trustgraph-flow/ /root/build/trustgraph-flow/
COPY trustgraph-vertexai/ /root/build/trustgraph-vertexai/
COPY trustgraph-bedrock/ /root/build/trustgraph-bedrock/
COPY trustgraph-parquet/ /root/build/trustgraph-parquet/
COPY trustgraph-embeddings-hf/ /root/build/trustgraph-embeddings-hf/
COPY trustgraph-utils/ /root/build/trustgraph-utils/

WORKDIR /root/build/

RUN pip3 wheel -w /root/wheels/ --no-deps ./trustgraph-base/
RUN pip3 wheel -w /root/wheels/ --no-deps ./trustgraph-flow/
RUN pip3 wheel -w /root/wheels/ --no-deps ./trustgraph-vertexai/
RUN pip3 wheel -w /root/wheels/ --no-deps ./trustgraph-bedrock/
RUN pip3 wheel -w /root/wheels/ --no-deps ./trustgraph-parquet/
RUN pip3 wheel -w /root/wheels/ --no-deps ./trustgraph-embeddings-hf/
RUN pip3 wheel -w /root/wheels/ --no-deps ./trustgraph-utils/

RUN ls /root/wheels

# ----------------------------------------------------------------------------
# Finally, the target container.  Start with base and add the package.
# ----------------------------------------------------------------------------

FROM ai

COPY --from=build /root/wheels /root/wheels

RUN \
    pip3 install /root/wheels/trustgraph_base-* && \
    pip3 install /root/wheels/trustgraph_flow-* && \
    pip3 install /root/wheels/trustgraph_vertexai-* && \
    pip3 install /root/wheels/trustgraph_bedrock-* && \
    pip3 install /root/wheels/trustgraph_parquet-* && \
    pip3 install /root/wheels/trustgraph_embeddings_hf-* && \
    pip3 install /root/wheels/trustgraph_utils-* && \
    pip3 cache purge && \
    rm -rf /root/wheels

WORKDIR /

CMD sleep 1000000

