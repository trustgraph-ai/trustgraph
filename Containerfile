
# ----------------------------------------------------------------------------
# Build an AI container.  This does the torch install which is huge, and I
# like to avoid re-doing this.
# ----------------------------------------------------------------------------

# This is painful.  Because of pulsar-client, we're stuck with Python 3.12

FROM docker.io/fedora:41 AS ai

ENV PIP_BREAK_SYSTEM_PACKAGES=1

RUN dnf update -y
RUN dnf install -y python3.13 pip3.13

#RUN alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1
#RUN alternatives --install /usr/bin/python python /usr/bin/python3.12 1
#RUN python3.12 -m ensurepip

RUN pip3 install torch --index-url https://download.pytorch.org/whl/cpu

RUN pip3 install wheel aiohttp rdflib anthropic boto3 cohere openai \
    google-cloud-aiplatform ollama google-generativeai langchain \
    langchain-core langchain-huggingface langchain-text-splitters \
    langchain-community pymilvus sentence-transformers transformers \
    huggingface-hub pulsar-client cassandra-driver pyyaml \
    neo4j tiktoken falkordb && \
    pip3 cache purge

# Most commonly used embeddings model, just build it into the container
# image
RUN huggingface-cli download sentence-transformers/all-MiniLM-L6-v2

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
COPY trustgraph-embeddings-hf/ /root/build/trustgraph-embeddings-hf/
COPY trustgraph-cli/ /root/build/trustgraph-cli/

WORKDIR /root/build/

RUN pip3 wheel -w /root/wheels/ --no-deps ./trustgraph-base/
RUN pip3 wheel -w /root/wheels/ --no-deps ./trustgraph-flow/
RUN pip3 wheel -w /root/wheels/ --no-deps ./trustgraph-vertexai/
RUN pip3 wheel -w /root/wheels/ --no-deps ./trustgraph-bedrock/
RUN pip3 wheel -w /root/wheels/ --no-deps ./trustgraph-embeddings-hf/
RUN pip3 wheel -w /root/wheels/ --no-deps ./trustgraph-cli/

# ----------------------------------------------------------------------------
# Finally, the target container.  Start with base and add the package.
# ----------------------------------------------------------------------------

FROM ai

COPY --from=build /root/wheels /root/wheels

# RUN dnf install -y python3-grpcio-1.48.4 python3-grpcio-tools-1.48.4

# RUN \
#     pip3 install /root/wheels/trustgraph_base-* && \
#     pip3 install /root/wheels/trustgraph_flow-* && \
#     pip3 install /root/wheels/trustgraph_vertexai-* && \
#     pip3 install /root/wheels/trustgraph_bedrock-* && \
#     pip3 install /root/wheels/trustgraph_embeddings_hf-* && \
#     pip3 install /root/wheels/trustgraph_cli-* && \
#     pip3 cache purge && \
#     rm -rf /root/wheels

WORKDIR /

