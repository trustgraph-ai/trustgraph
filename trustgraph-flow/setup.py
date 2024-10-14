import setuptools
import os
import importlib

with open("README.md", "r") as fh:
    long_description = fh.read()

# Load a version number module
spec = importlib.util.spec_from_file_location(
    'version', 'trustgraph/flow_version.py'
)
version_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(version_module)

version = version_module.__version__

setuptools.setup(
    name="trustgraph-flow",
    version=version,
    author="trustgraph.ai",
    author_email="security@trustgraph.ai",
    description="TrustGraph provides a means to run a pipeline of flexible AI processing components in a flexible means to achieve a processing pipeline.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/trustgraph-ai/trustgraph",
    packages=setuptools.find_namespace_packages(
        where='./',
    ),
    classifiers=[ 
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
    download_url = "https://github.com/trustgraph-ai/trustgraph/archive/refs/tags/v" + version + ".tar.gz",
    install_requires=[
        "trustgraph-base>=0.13,<0.14",
        "urllib3",
        "rdflib",
        "pymilvus",
        "langchain",
        "langchain-core",
        "langchain-text-splitters",
        "langchain-community",
        "requests",
        "cassandra-driver",
        "pulsar-client",
        "pypdf",
        "qdrant-client",
        "tabulate",
        "anthropic",
        "pyyaml",
        "prometheus-client",
        "cohere",
        "openai",
        "neo4j",
        "tiktoken",
        "google-generativeai",
    ],
    scripts=[
        "scripts/chunker-recursive",
        "scripts/chunker-token",
        "scripts/de-query-milvus",
        "scripts/de-query-qdrant",
        "scripts/de-write-milvus",
        "scripts/de-write-qdrant",
        "scripts/document-rag",
        "scripts/embeddings-ollama",
        "scripts/embeddings-vectorize",
        "scripts/ge-query-milvus",
        "scripts/ge-query-qdrant",
        "scripts/ge-write-milvus",
        "scripts/ge-write-qdrant",
        "scripts/graph-rag",
        "scripts/kg-extract-definitions",
        "scripts/kg-extract-topics",
        "scripts/kg-extract-relationships",
        "scripts/metering",
        "scripts/object-extract-row",
        "scripts/oe-write-milvus",
        "scripts/pdf-decoder",
        "scripts/prompt-generic",
        "scripts/prompt-template",
        "scripts/rows-write-cassandra",
        "scripts/run-processing",
        "scripts/text-completion-azure",
        "scripts/text-completion-azure-openai",
        "scripts/text-completion-claude",
        "scripts/text-completion-cohere",
        "scripts/text-completion-googleaistudio",
        "scripts/text-completion-llamafile",
        "scripts/text-completion-ollama",
        "scripts/text-completion-openai",
        "scripts/triples-query-cassandra",
        "scripts/triples-query-neo4j",
        "scripts/triples-write-cassandra",
        "scripts/triples-write-neo4j",
    ]
)
