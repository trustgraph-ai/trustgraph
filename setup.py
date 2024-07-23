import setuptools
import os

with open("README.md", "r") as fh:
    long_description = fh.read()

version = "0.5.1"

setuptools.setup(
    name="trustgraph",
    version=version,
    author="trustgraph.ai",
    author_email="security@trustgraph.ai",
    description="TrustGraph provides a means to run a pipeline of flexible AI processing components in a flexible means to achieve a processing pipeline.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/trustgraph-ai/trustgraph",
    packages=setuptools.find_packages(),
    classifiers=[ 
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
    download_url = "https://github.com/trustgraph-ai/trustgraph/archive/refs/tags/v" + version + ".tar.gz",
    install_requires=[
        "torch",
        "urllib3",
        "transformers",
        "sentence-transformers",
        "rdflib",
        "pymilvus",
        "langchain",
        "langchain-core",
        "langchain-huggingface",
        "langchain-text-splitters",
        "langchain-community",
        "huggingface-hub",
        "requests",
        "cassandra-driver",
        "pulsar-client",
        "pypdf",
        "anthropic",
        "google-cloud-aiplatform",
        "pyyaml",
        "prometheus-client",
    ],
    scripts=[
        "scripts/chunker-recursive",
        "scripts/embeddings-hf",
        "scripts/embeddings-ollama",
        "scripts/embeddings-vectorize",
        "scripts/ge-write-milvus",
        "scripts/graph-rag",
        "scripts/graph-show",
        "scripts/graph-to-turtle",
        "scripts/init-pulsar-manager",
        "scripts/kg-extract-definitions",
        "scripts/kg-extract-relationships",
        "scripts/loader",
        "scripts/pdf-decoder",
        "scripts/query",
        "scripts/run-processing",
        "scripts/text-completion-azure",
        "scripts/text-completion-claude",
        "scripts/text-completion-ollama",
        "scripts/text-completion-vertexai",
        "scripts/triples-write-cassandra",
    ]
)
